import uuid
from datetime import date, timedelta

from django.db import models
from django.utils import timezone


class BeltLevel(models.TextChoices):
    WHITE = 'WHITE', 'White'
    WHITE_YELLOW = 'WHITE_YELLOW', 'White-Yellow'
    YELLOW = 'YELLOW', 'Yellow'
    YELLOW_GREEN = 'YELLOW_GREEN', 'Yellow-Green'
    GREEN = 'GREEN', 'Green'
    GREEN_BLUE = 'GREEN_BLUE', 'Green-Blue'
    BLUE = 'BLUE', 'Blue'
    BLUE_RED = 'BLUE_RED', 'Blue-Red'
    RED = 'RED', 'Red'
    RED_BLACK = 'RED_BLACK', 'Red-Black'
    BLACK = 'BLACK', 'Black'


class MemberTier(models.TextChoices):
    COLOUR_BELT = 'COLOUR_BELT', 'Colour Belt'       # HK$100
    POOM = 'POOM', 'Poom'                             # HK$800
    STUDENT_BLACK = 'STUDENT_BLACK', 'Student Black'  # HK$800
    ADULT_BLACK = 'ADULT_BLACK', 'Adult Black'        # HK$1,200
    OVERSEAS_BLACK = 'OVERSEAS_BLACK', 'Overseas Black'  # HK$1,200


class MemberStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    GRADUATED = 'GRADUATED', 'Graduated'


class MemberProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='member_profile',
    )
    member_id = models.CharField(max_length=30, unique=True)
    chinese_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=150)
    emergency_contact_phone = models.CharField(max_length=30)
    current_belt = models.CharField(
        max_length=20, choices=BeltLevel.choices, default=BeltLevel.WHITE
    )
    tier = models.CharField(
        max_length=20, choices=MemberTier.choices, default=MemberTier.COLOUR_BELT
    )
    status = models.CharField(
        max_length=15, choices=MemberStatus.choices, default=MemberStatus.ACTIVE
    )
    primary_dojo = models.ForeignKey(
        'dojos.DojoEntity',
        on_delete=models.PROTECT,
        related_name='primary_members',
    )
    joined_date = models.DateField()
    notes = models.TextField(blank=True)
    public_showcase_consent = models.BooleanField(
        default=False,
        help_text='Staff-set only: permission to feature this member (name, belt, dojo) on the public website.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['member_id']

    def __str__(self):
        return f'{self.member_id} — {self.full_name}'

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def age(self):
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def is_active(self):
        return self.status == MemberStatus.ACTIVE

    @property
    def is_minor(self):
        return self.age < 18


class MemberDojoEnrollment(models.Model):
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    dojo = models.ForeignKey(
        'dojos.DojoEntity',
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    enrolled_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'dojo'],
                name='unique_member_dojo_enrollment',
            )
        ]

    def __str__(self):
        return f'{self.member} @ {self.dojo}'


class BeltPromotionRecord(models.Model):
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='belt_promotions',
    )
    belt = models.CharField(max_length=20, choices=BeltLevel.choices)
    promoted_date = models.DateField()
    dojo = models.ForeignKey(
        'dojos.DojoEntity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='belt_promotions',
    )
    promoted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotions_awarded',
    )
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-promoted_date']

    def __str__(self):
        return f'{self.member} — {self.get_belt_display()} ({self.promoted_date})'


class MemberCertificate(models.Model):
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='certificates',
    )
    certificate_name = models.CharField(max_length=200)
    issuing_body = models.CharField(max_length=200, blank=True)
    date_acquired = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-date_acquired']

    def __str__(self):
        return f'{self.member} — {self.certificate_name}'


class GuardianRelationship(models.TextChoices):
    FATHER = 'FATHER', 'Father'
    MOTHER = 'MOTHER', 'Mother'
    GUARDIAN = 'GUARDIAN', 'Guardian'
    OTHER = 'OTHER', 'Other'


class MemberGuardian(models.Model):
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='guardians',
    )
    guardian = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='guardian_of',
    )
    relationship = models.CharField(max_length=20, choices=GuardianRelationship.choices)
    is_primary = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'guardian']
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'guardian'],
                name='unique_member_guardian',
            )
        ]

    def __str__(self):
        return f'{self.guardian} — {self.get_relationship_display()} of {self.member}'


class InvitationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    EXPIRED = 'EXPIRED', 'Expired'
    REVOKED = 'REVOKED', 'Revoked'


def generate_member_id():
    year = timezone.now().year
    suffix = uuid.uuid4().hex[:6].upper()
    return f'MEM-{year}-{suffix}'


class RegistrationInvitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    contact_email = models.EmailField()
    target_dojo = models.ForeignKey(
        'dojos.DojoEntity',
        on_delete=models.PROTECT,
        related_name='invitations',
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='issued_invitations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.contact_email} — {self.target_dojo} [{self.status}]'

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.status == InvitationStatus.PENDING and timezone.now() <= self.expires_at
