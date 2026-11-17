from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.accounts.mixins import RoleRequiredMixin
from apps.activities.models import CoachCertificationRecord
from apps.dojos.models import DojoEntity, DojoStaff
from apps.members.forms import InvitationRequestForm, MemberContactForm, MemberProfileForm, OnboardingForm
from apps.members.models import (
    InvitationStatus,
    MemberGuardian,
    MemberProfile,
    RegistrationInvitation,
    generate_member_id,
)
from apps.members.services import send_invitation_email
from apps.payments.models import PaymentRecord

User = get_user_model()

COACH_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN', 'COACH']
ADMIN_ROLES = ['GRANDMASTER', 'DEPUTY_GRANDMASTER', 'ADMIN']


class DojoScopedQuerysetMixin:
    """
    Restricts the queryset to members enrolled at the requesting COACH's own
    dojo(s). GRANDMASTER/DEPUTY_GRANDMASTER/ADMIN see all members unfiltered.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'COACH':
            coach_dojos = DojoStaff.objects.filter(
                user=self.request.user, is_active=True
            ).values_list('dojo_id', flat=True)
            qs = qs.filter(enrollments__dojo_id__in=coach_dojos).distinct()
        return qs


class MemberListView(LoginRequiredMixin, RoleRequiredMixin, DojoScopedQuerysetMixin, ListView):
    roles = COACH_ROLES
    model = MemberProfile
    template_name = 'members/member_list.html'
    context_object_name = 'members'


class MemberDetailView(LoginRequiredMixin, RoleRequiredMixin, DojoScopedQuerysetMixin, DetailView):
    roles = COACH_ROLES
    model = MemberProfile
    template_name = 'members/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.object
        context['dojo_staff_roles'] = (
            DojoStaff.objects.filter(user=member.user).select_related('dojo')
        )
        context['coach_certifications'] = (
            CoachCertificationRecord.objects.filter(activity_application__member=member)
            .select_related('activity_application')
            .order_by('-exam_date')
        )
        context['belt_promotions'] = member.belt_promotions.select_related('dojo', 'promoted_by')
        context['certificates'] = member.certificates.all()
        context['guardians'] = member.guardians.select_related('guardian')

        if self.request.user.role in ADMIN_ROLES:
            context['can_view_payments'] = True
            context['annual_fees'] = member.annual_fees.select_related('invoice').order_by('-year')
            context['payment_records'] = (
                PaymentRecord.objects.filter(annual_fee__member=member)
                .select_related('annual_fee', 'confirmed_by')
                .order_by('-created_at')
            )
        return context


class MemberUpdateView(LoginRequiredMixin, RoleRequiredMixin, View):
    roles = ADMIN_ROLES
    template_name = 'members/member_form.html'

    def get_object(self):
        return get_object_or_404(MemberProfile, pk=self.kwargs['pk'])

    def get(self, request, *args, **kwargs):
        member = self.get_object()
        context = {
            'member': member,
            'user_form': MemberContactForm(instance=member.user),
            'profile_form': MemberProfileForm(instance=member),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        member = self.get_object()
        user_form = MemberContactForm(request.POST, instance=member.user)
        profile_form = MemberProfileForm(request.POST, instance=member)
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            return redirect('members:member_detail', pk=member.pk)
        context = {'member': member, 'user_form': user_form, 'profile_form': profile_form}
        return render(request, self.template_name, context)


class MemberInvitationCreateView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    roles = COACH_ROLES
    template_name = 'members/invitation_form.html'
    form_class = InvitationRequestForm

    def get_dojo_queryset(self):
        if self.request.user.role == 'COACH':
            coach_dojos = DojoStaff.objects.filter(
                user=self.request.user, is_active=True
            ).values_list('dojo_id', flat=True)
            return DojoEntity.objects.filter(id__in=coach_dojos)
        return DojoEntity.objects.filter(is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dojo_queryset'] = self.get_dojo_queryset()
        return kwargs

    def form_valid(self, form):
        invitation = form.save(commit=False)
        invitation.created_by = self.request.user
        invitation.save()
        onboarding_url = self.request.build_absolute_uri(
            reverse('members:onboarding', args=[invitation.token])
        )
        email_sent = True
        try:
            send_invitation_email(invitation, onboarding_url)
        except Exception:
            email_sent = False
        return render(self.request, 'members/invitation_sent.html', {
            'invitation': invitation,
            'onboarding_url': onboarding_url,
            'email_sent': email_sent,
        })


class MemberOnboardingView(View):
    """
    Public, no-login registration form reached via a magic link. Creates a
    guardian User (role=PARENT, real password) and a member User+MemberProfile
    (role=MEMBER, unusable password), linked via MemberGuardian.
    """

    @staticmethod
    def _unique_username(base):
        base = slugify(base) or 'user'
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f'{base}{suffix}'
        return username

    def get(self, request, token):
        invitation = get_object_or_404(RegistrationInvitation, token=token)
        if not invitation.is_valid():
            return render(request, 'members/onboarding_invalid.html', {'invitation': invitation}, status=410)
        return render(request, 'members/onboarding_form.html', {
            'invitation': invitation, 'form': OnboardingForm(),
        })

    def post(self, request, token):
        invitation = get_object_or_404(RegistrationInvitation, token=token)
        if not invitation.is_valid():
            return render(request, 'members/onboarding_invalid.html', {'invitation': invitation}, status=410)

        form = OnboardingForm(request.POST)
        if not form.is_valid():
            return render(request, 'members/onboarding_form.html', {'invitation': invitation, 'form': form})

        data = form.cleaned_data
        with transaction.atomic():
            guardian_username = self._unique_username(invitation.contact_email.split('@')[0])
            guardian_user = User.objects.create_user(
                username=guardian_username,
                email=invitation.contact_email,
                password=data['password'],
                first_name=data['guardian_first_name'],
                last_name=data['guardian_last_name'],
                phone=data['guardian_phone'],
                role=User.Role.PARENT,
            )

            member_id = generate_member_id()
            member_user = User.objects.create_user(
                username=member_id.lower(),
                password=None,
                first_name=data['member_first_name'],
                last_name=data['member_last_name'],
                role=User.Role.MEMBER,
            )

            member_profile = MemberProfile.objects.create(
                user=member_user,
                member_id=member_id,
                chinese_name=data['member_chinese_name'],
                date_of_birth=data['date_of_birth'],
                gender=data['gender'],
                height_cm=data['height_cm'],
                weight_kg=data['weight_kg'],
                emergency_contact_name=data['emergency_contact_name'],
                emergency_contact_phone=data['emergency_contact_phone'],
                primary_dojo=invitation.target_dojo,
                joined_date=timezone.now().date(),
            )
            MemberGuardian.objects.create(
                member=member_profile,
                guardian=guardian_user,
                relationship=data['relationship'],
                is_primary=True,
            )
            invitation.status = InvitationStatus.COMPLETED
            invitation.save()

        return redirect('members:onboarding_thanks', token=token)


class MemberOnboardingThanksView(TemplateView):
    template_name = 'members/onboarding_success.html'
