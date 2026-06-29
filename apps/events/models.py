from django.conf import settings
from django.db import models


class EventType(models.TextChoices):
    TRAINING = 'TRAINING', 'Training'
    EXAM = 'EXAM', 'Exam'
    TOURNAMENT = 'TOURNAMENT', 'Tournament'
    OTHER = 'OTHER', 'Other'


class EventStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    CANCELLED = 'CANCELLED', 'Cancelled'
    COMPLETED = 'COMPLETED', 'Completed'


class CheckInMethod(models.TextChoices):
    QR_SCAN = 'QR_SCAN', 'QR Scan'
    MANUAL = 'MANUAL', 'Manual'
    COACH_MARKED = 'COACH_MARKED', 'Coach Marked'


class Event(models.Model):
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.DRAFT)
    dojo = models.ForeignKey('dojos.DojoEntity', on_delete=models.PROTECT, related_name='events')
    location = models.CharField(max_length=300, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    max_capacity = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime']

    def __str__(self):
        return f'{self.title} ({self.get_event_type_display()})'

    @property
    def attendance_count(self):
        return self.attendancelog_set.count()

    @property
    def is_full(self):
        if self.max_capacity is None:
            return False
        return self.attendancelog_set.count() >= self.max_capacity


class AttendanceLog(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    member = models.ForeignKey('members.MemberProfile', on_delete=models.CASCADE, related_name='attendance_logs')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    check_in_method = models.CharField(max_length=20, choices=CheckInMethod.choices)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-checked_in_at']
        constraints = [
            models.UniqueConstraint(fields=['event', 'member'], name='unique_member_per_event'),
        ]

    def __str__(self):
        return f'{self.member} @ {self.event} ({self.checked_in_at:%Y-%m-%d})'
