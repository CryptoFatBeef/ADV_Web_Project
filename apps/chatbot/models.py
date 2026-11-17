from django.conf import settings
from django.db import models


class FAQCategory(models.TextChoices):
    MEMBERSHIP = 'MEMBERSHIP',  'Membership'
    FEES = 'FEES',        'Fees & Payment'
    TRAINING = 'TRAINING',    'Training'
    EXAMS = 'EXAMS',       'Exams & Grading'
    TOURNAMENTS = 'TOURNAMENTS', 'Tournaments'
    GENERAL = 'GENERAL',     'General'


class FAQEntry(models.Model):
    category = models.CharField(
        max_length=20,
        choices=FAQCategory.choices,
        default=FAQCategory.GENERAL,
    )
    question = models.CharField(max_length=500)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='faq_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order', 'question']
        verbose_name = 'FAQ Entry'

    def __str__(self):
        return f'[{self.get_category_display()}] {self.question[:80]}'


class ChatSession(models.Model):
    session_key = models.CharField(max_length=100, unique=True)
    # Null = anonymous public user (FAQ bot is public-facing)
    member = models.ForeignKey(
        'members.MemberProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='chat_sessions'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-last_active']

    def __str__(self):
        return f'Session {self.session_key} ({self.started_at.date()})'


class ChatMessage(models.Model):

    class Role(models.TextChoices):
        USER = 'user',      'User'
        ASSISTANT = 'assistant', 'Assistant'

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # Token usage — for cost tracking and rate limiting
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role} @ {self.session} [{self.created_at:%H:%M}]'
