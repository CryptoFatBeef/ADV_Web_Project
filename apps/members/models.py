from datetime import date

from django.db import models


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
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
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
