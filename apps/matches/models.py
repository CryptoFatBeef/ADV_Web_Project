from django.db import models

from apps.members.models import BeltLevel


class MatchType(models.TextChoices):
    SPARRING = 'SPARRING', '搏擊'
    POOMSAE  = 'POOMSAE',  '品勢'
    BREAKING = 'BREAKING', '破板'
    OTHER    = 'OTHER',    '其他'


class MatchResult(models.TextChoices):
    WIN          = 'WIN',          'Win'
    LOSS         = 'LOSS',         'Loss'
    DRAW         = 'DRAW',         'Draw'
    DISQUALIFIED = 'DISQUALIFIED', 'Disqualified'
    WITHDREW     = 'WITHDREW',     'Withdrew'
    BYE          = 'BYE',          'Bye'


class WeightClass(models.TextChoices):
    FINWEIGHT     = 'FINWEIGHT',     'Fin'
    FLYWEIGHT     = 'FLYWEIGHT',     'Fly'
    BANTAMWEIGHT  = 'BANTAMWEIGHT',  'Bantam'
    FEATHERWEIGHT = 'FEATHERWEIGHT', 'Feather'
    LIGHTWEIGHT   = 'LIGHTWEIGHT',   'Light'
    WELTERWEIGHT  = 'WELTERWEIGHT',  'Welter'
    MIDDLEWEIGHT  = 'MIDDLEWEIGHT',  'Middle'
    HEAVYWEIGHT   = 'HEAVYWEIGHT',   'Heavy'
    OPEN          = 'OPEN',          'Open'


class Medal(models.TextChoices):
    GOLD   = 'GOLD',   'Gold'
    SILVER = 'SILVER', 'Silver'
    BRONZE = 'BRONZE', 'Bronze'
    NONE   = 'NONE',   'None'


class DeviceType(models.TextChoices):
    VEST      = 'VEST',      'Vest'
    RECEIVER  = 'RECEIVER',  'Receiver'
    HEADGUARD = 'HEADGUARD', 'Headguard'


class Tournament(models.Model):
    name             = models.CharField(max_length=200)
    event            = models.ForeignKey(
        'events.Event', on_delete=models.PROTECT, related_name='tournaments'
    )
    match_type       = models.CharField(max_length=20, choices=MatchType.choices)
    organised_by     = models.CharField(max_length=200, blank=True)
    location         = models.CharField(max_length=300, blank=True)
    is_international = models.BooleanField(default=False)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event__start_datetime', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_match_type_display()})'


class MatchEntry(models.Model):
    tournament    = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name='entries'
    )
    member        = models.ForeignKey(
        'members.MemberProfile', on_delete=models.PROTECT, related_name='match_entries'
    )
    belt_at_match = models.CharField(max_length=20, choices=BeltLevel.choices)
    weight_class  = models.CharField(max_length=20, choices=WeightClass.choices, blank=True)
    result        = models.CharField(max_length=15, choices=MatchResult.choices, blank=True)
    medal         = models.CharField(max_length=10, choices=Medal.choices, default=Medal.NONE)
    placement     = models.PositiveSmallIntegerField(null=True, blank=True)
    opponent_name = models.CharField(max_length=200, blank=True)
    score         = models.CharField(max_length=50, blank=True)
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['tournament', 'member']
        verbose_name        = 'Match Entry'
        verbose_name_plural = 'Match Entries'
        constraints = [
            models.UniqueConstraint(
                fields=['tournament', 'member'],
                name='unique_member_per_tournament',
            )
        ]

    def __str__(self):
        return f'{self.member} @ {self.tournament} [{self.get_result_display() or "Pending"}]'


# KPNPDevice — STUB: KP&P electronic scoring hardware inventory.
# No business logic. Data model only. Integration deferred to a future phase.
class KPNPDevice(models.Model):
    device_type   = models.CharField(max_length=20, choices=DeviceType.choices)
    serial_number = models.CharField(max_length=100, unique=True)
    tournament    = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kpnp_devices',
    )
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['device_type', 'serial_number']
        verbose_name        = 'KP&P Device'
        verbose_name_plural = 'KP&P Devices'

    def __str__(self):
        return f'{self.get_device_type_display()} — {self.serial_number}'
