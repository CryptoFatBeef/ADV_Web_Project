from django.conf import settings
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition

from apps.skills.models import SkillResult


class ActivityType(models.TextChoices):
    BELT_GRADING = 'BELT_GRADING', 'Belt Grading'
    REFEREE_PROMOTION = 'REFEREE_PROMOTION', 'Referee Promotion'
    COMPETITION_APPLICATION = 'COMPETITION_APPLICATION', 'Competition Application'
    COACH_CERTIFICATION = 'COACH_CERTIFICATION', 'Coach Certification'
    OTHER = 'OTHER', 'Other'


class ApplicationStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    AWAITING_COACH_REC = 'AWAITING_COACH_REC', 'Awaiting Coach Recommendation'
    AWAITING_GM_APPROVAL = 'AWAITING_GM_APPROVAL', 'Awaiting GM Approval'
    PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
    PROCESSING_PDF = 'PROCESSING_PDF', 'Processing PDF'
    COMPLETED = 'COMPLETED', 'Completed'
    REJECTED = 'REJECTED', 'Rejected'


class ActivityTemplate(models.Model):
    name = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    form_schema = models.JSONField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='activity_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_activity_type_display()})'


class ActivityEvent(models.Model):
    template = models.ForeignKey(
        ActivityTemplate,
        on_delete=models.PROTECT,
        related_name='events',
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.PROTECT,
        related_name='activity_events',
    )
    scheduled_date = models.DateField()
    dojo = models.ForeignKey(
        'dojos.DojoEntity',
        on_delete=models.PROTECT,
        related_name='activity_events',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f'{self.template} @ {self.dojo} on {self.scheduled_date}'


class ActivityApplication(models.Model):
    activity_event = models.ForeignKey(
        ActivityEvent,
        on_delete=models.PROTECT,
        related_name='applications',
    )
    member = models.ForeignKey(
        'members.MemberProfile',
        on_delete=models.CASCADE,
        related_name='activity_applications',
    )
    form_data = models.JSONField(default=dict)
    state = FSMField(default='DRAFT', protected=True)
    coach_recommendation = models.TextField(blank=True)
    gm_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        constraints = [
            models.UniqueConstraint(
                fields=['activity_event', 'member'],
                name='unique_member_activity_event',
            )
        ]

    def __str__(self):
        return f'{self.member} — {self.activity_event} [{self.state}]'

    @transition(field=state, source='DRAFT', target='AWAITING_COACH_REC')
    def submit(self):
        self.submitted_at = timezone.now()

    @transition(field=state, source='AWAITING_COACH_REC', target='AWAITING_GM_APPROVAL')
    def recommend(self):
        pass

    @transition(field=state, source='AWAITING_GM_APPROVAL', target='PENDING_PAYMENT')
    def approve(self):
        pass

    @transition(field=state, source='AWAITING_GM_APPROVAL', target='REJECTED')
    def reject(self):
        pass

    @transition(field=state, source='PENDING_PAYMENT', target='PROCESSING_PDF')
    def confirm_payment(self):
        pass

    @transition(field=state, source='PROCESSING_PDF', target='COMPLETED')
    def complete(self):
        self.completed_at = timezone.now()


class CoachCertificationRecord(models.Model):
    activity_application = models.OneToOneField(
        ActivityApplication,
        on_delete=models.CASCADE,
        related_name='coach_certification',
    )
    certifying_body = models.CharField(max_length=200, default='HKTKDA')
    course_name = models.CharField(max_length=200)
    exam_date = models.DateField()
    result = models.CharField(max_length=10, choices=SkillResult.choices)
    certificate_number = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f'{self.activity_application.member} — {self.course_name} [{self.result}]'
