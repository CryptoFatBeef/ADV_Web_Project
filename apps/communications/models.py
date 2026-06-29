from django.db import models


class NotificationChannel(models.TextChoices):
    IN_APP = 'IN_APP', 'In-App'
    EMAIL = 'EMAIL', 'Email'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'


class NotificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    DELIVERED = 'DELIVERED', 'Delivered'
    FAILED = 'FAILED', 'Failed'
    READ = 'READ', 'Read'


class NotificationTemplate(models.Model):
    name = models.CharField(max_length=200, unique=True)
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    subject = models.CharField(max_length=300, blank=True)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} [{self.get_channel_display()}]"


class Notification(models.Model):
    recipient = models.ForeignKey(
        'members.MemberProfile', on_delete=models.CASCADE, related_name='notifications'
    )
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.PROTECT,
        related_name='notifications', null=True, blank=True
    )
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    subject = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    status = models.CharField(
        max_length=10, choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient} via {self.channel} [{self.status}]"
