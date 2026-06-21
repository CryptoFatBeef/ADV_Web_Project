from django.db import models
from django.db.models import Q


class DojoEntity(models.Model):
    class District(models.TextChoices):
        KWAI_CHUNG = 'KwaiChung', 'Kwai Chung'
        TUEN_MUN = 'TuenMun', 'Tuen Mun'
        TAI_PO = 'TaiPo', 'Tai Po'
        MA_ON_SHAN = 'MaOnShan', 'Ma On Shan'
        LAM_TIN = 'LamTin', 'Lam Tin'
        KOWLOON_TONG = 'KowloonTong', 'Kowloon Tong'
        SHAM_SHUI_PO = 'ShamShuiPo', 'Sham Shui Po'
        WONG_TAI_SIN = 'WongTaiSin', 'Wong Tai Sin'
        TSUEN_WAN = 'TsuenWan', 'Tsuen Wan'
        YUEN_LONG = 'YuenLong', 'Yuen Long'
        SHA_TIN = 'ShaTin', 'Sha Tin'
        TSEUNG_KWAN_O = 'TseungKwanO', 'Tseung Kwan O'
        CENTRAL = 'Central', 'Central'
        WAN_CHAI = 'WanChai', 'Wan Chai'
        CAUSEWAY_BAY = 'CausewayBay', 'Causeway Bay'

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    address = models.TextField()
    district = models.CharField(max_length=30, choices=District.choices)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'dojo entities'
        ordering = ['name']

    def __str__(self):
        return self.name


class DojoStaff(models.Model):
    class Role(models.TextChoices):
        HEAD_COACH = 'HEAD_COACH', 'Head Coach'
        ASSISTANT_COACH = 'ASSISTANT_COACH', 'Assistant Coach'
        ADMIN_STAFF = 'ADMIN_STAFF', 'Admin Staff'

    dojo = models.ForeignKey(
        DojoEntity, on_delete=models.PROTECT, related_name='staff'
    )
    user = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='dojo_roles'
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    joined_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['dojo'],
                condition=Q(role='HEAD_COACH'),
                name='unique_head_coach_per_dojo',
            )
        ]

    def __str__(self):
        return f'{self.user} — {self.role} @ {self.dojo}'
