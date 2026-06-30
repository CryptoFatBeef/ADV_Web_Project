from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView

from apps.cms.models import ContentStatus, NewsPost
from apps.dojos.models import DojoEntity, DojoStaff
from apps.members.models import MemberProfile, MemberStatus, MemberTier

BLACK_BELT_TIERS = [
    MemberTier.STUDENT_BLACK,
    MemberTier.ADULT_BLACK,
    MemberTier.OVERSEAS_BLACK,
    MemberTier.POOM,
]


class HomeView(TemplateView):
    template_name = 'public/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_news'] = NewsPost.objects.filter(
            status=ContentStatus.PUBLISHED, published_at__lte=timezone.now()
        )[:3]
        context['featured_dojos'] = DojoEntity.objects.filter(is_active=True)[:4]
        return context


class AboutView(TemplateView):
    template_name = 'public/about.html'


class InstructorListView(ListView):
    model = DojoStaff
    template_name = 'public/instructors.html'
    context_object_name = 'instructors'
    queryset = DojoStaff.objects.filter(is_public=True, is_active=True).select_related('user', 'dojo')


class PublicDojoListView(ListView):
    model = DojoEntity
    template_name = 'public/dojo_list.html'
    context_object_name = 'dojos'
    queryset = DojoEntity.objects.filter(is_active=True)


class PublicDojoDetailView(DetailView):
    model = DojoEntity
    template_name = 'public/dojo_detail.html'
    context_object_name = 'dojo'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    queryset = DojoEntity.objects.filter(is_active=True)


class NewsListView(ListView):
    model = NewsPost
    template_name = 'public/news_list.html'
    context_object_name = 'news_posts'
    paginate_by = 10
    queryset = NewsPost.objects.filter(status=ContentStatus.PUBLISHED, published_at__lte=timezone.now())


class NewsDetailView(DetailView):
    model = NewsPost
    template_name = 'public/news_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    queryset = NewsPost.objects.filter(status=ContentStatus.PUBLISHED, published_at__lte=timezone.now())


class ShowcaseListView(ListView):
    model = MemberProfile
    template_name = 'public/showcase_list.html'
    context_object_name = 'black_belts'
    queryset = MemberProfile.objects.filter(
        public_showcase_consent=True,
        status=MemberStatus.ACTIVE,
        tier__in=BLACK_BELT_TIERS,
    ).select_related('user', 'primary_dojo')


class RobotsTxtView(TemplateView):
    template_name = 'public/robots.txt'
    content_type = 'text/plain'
