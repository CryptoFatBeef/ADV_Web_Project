from django.conf import settings
from django.db import models
from django.utils import timezone


class PageSection(models.TextChoices):
    HOME = 'HOME',     'Home'
    ABOUT = 'ABOUT',    'About'
    COACHES = 'COACHES',  'Coaches'
    SCHEDULE = 'SCHEDULE', 'Schedule'
    NEWS = 'NEWS',     'News'
    CONTACT = 'CONTACT',  'Contact'
    OTHER = 'OTHER',    'Other'


class ContentStatus(models.TextChoices):
    DRAFT = 'DRAFT',     'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    ARCHIVED = 'ARCHIVED',  'Archived'


class ContentBlock(models.Model):
    title = models.CharField(max_length=200)
    section = models.CharField(max_length=20, choices=PageSection.choices)
    status = models.CharField(max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT)
    order = models.PositiveIntegerField(default=0)
    body = models.TextField()
    image = models.ImageField(upload_to='cms/', blank=True)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='content_blocks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['section', 'order', '-published_at']

    def __str__(self):
        return f'{self.section} — {self.title}'


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT)
    is_pinned = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='announcements',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-published_at']

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        now = timezone.now()
        if self.status != ContentStatus.PUBLISHED:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True


class NewsPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    status = models.CharField(max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT)
    excerpt = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    cover_image = models.ImageField(upload_to='news/', blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='news_posts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title
