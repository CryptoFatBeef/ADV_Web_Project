from django.db import models


class LeadStatus(models.TextChoices):
    NEW = 'NEW', 'New'
    CONTACTED = 'CONTACTED', 'Contacted'
    ENROLLED = 'ENROLLED', 'Enrolled'
    DECLINED = 'DECLINED', 'Declined'


class EnrollmentLead(models.Model):
    full_name = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=30)
    contact_email = models.EmailField(blank=True)
    interested_dojo = models.ForeignKey(
        'dojos.DojoEntity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollment_leads',
    )
    child_age = models.PositiveSmallIntegerField(null=True, blank=True)
    message = models.TextField(blank=True)
    consent_pdpo = models.BooleanField(
        default=False,
        help_text='Required: explicit consent under Hong Kong PDPO for collecting personal data.',
    )
    status = models.CharField(max_length=15, choices=LeadStatus.choices, default=LeadStatus.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.get_status_display()})'
