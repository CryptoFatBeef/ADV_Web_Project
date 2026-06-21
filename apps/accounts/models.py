from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        GRANDMASTER = 'GRANDMASTER', 'Grandmaster'
        DEPUTY_GRANDMASTER = 'DEPUTY_GRANDMASTER', 'Deputy Grandmaster'
        ADMIN = 'ADMIN', 'Admin'
        EDITOR = 'EDITOR', 'Editor'
        COACH = 'COACH', 'Coach'
        MEMBER = 'MEMBER', 'Member'
        PARENT = 'PARENT', 'Parent'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
