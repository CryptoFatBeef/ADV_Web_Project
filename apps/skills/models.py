from django.conf import settings
from django.db import models

from apps.members.models import BeltLevel


class SkillCategory(models.TextChoices):
    HAND_TECHNIQUE = 'HAND_TECHNIQUE', 'Hand Technique'
    FOOT_TECHNIQUE = 'FOOT_TECHNIQUE', 'Foot Technique'
    POOMSAE = 'POOMSAE', 'Poomsae'
    BREAKING = 'BREAKING', 'Breaking'
    SPARRING = 'SPARRING', 'Sparring'
    FITNESS = 'FITNESS', 'Fitness'
    OTHER = 'OTHER', 'Other'


class SkillResult(models.TextChoices):
    PASS = 'PASS', 'Pass'
    FAIL = 'FAIL', 'Fail'
    EXEMPTED = 'EXEMPTED', 'Exempted'


class SkillRecord(models.Model):
    member = models.ForeignKey(
        'members.MemberProfile',
        on_delete=models.CASCADE,
        related_name='skill_records',
    )
    activity_application = models.ForeignKey(
        'activities.ActivityApplication',
        on_delete=models.PROTECT,
        related_name='skill_records',
    )
    skill_name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=SkillCategory.choices)
    result = models.CharField(max_length=10, choices=SkillResult.choices)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assessed_skills',
    )
    assessed_at = models.DateField()
    belt_level_at_assessment = models.CharField(max_length=20, choices=BeltLevel.choices)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-assessed_at', 'category']
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'activity_application', 'skill_name'],
                name='unique_skill_per_member_per_exam',
            )
        ]

    def __str__(self):
        return f'{self.member} — {self.skill_name} [{self.result}]'
