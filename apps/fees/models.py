import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.members.models import MemberProfile, MemberTier


class FeeStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partial'
    PAID = 'PAID', 'Paid'
    WAIVED = 'WAIVED', 'Waived'
    OVERDUE = 'OVERDUE', 'Overdue'


def generate_invoice_number():
    year = timezone.now().year
    suffix = uuid.uuid4().hex[:6].upper()
    return f'INV-{year}-{suffix}'


class AnnualFee(models.Model):
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.PROTECT,
        related_name='annual_fees',
    )
    year = models.PositiveIntegerField()
    tier_at_billing = models.CharField(max_length=20, choices=MemberTier.choices)
    amount_due = models.DecimalField(max_digits=8, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10,
        choices=FeeStatus.choices,
        default=FeeStatus.UNPAID,
    )
    due_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'year'],
                name='unique_annual_fee_per_member_per_year',
            )
        ]

    def __str__(self):
        return f'{self.member} — {self.year} ({self.get_status_display()})'

    @property
    def balance_due(self):
        return self.amount_due - self.amount_paid

    @property
    def is_overdue(self):
        return self.status != FeeStatus.PAID and self.due_date < timezone.now().date()


class Invoice(models.Model):
    annual_fee = models.OneToOneField(
        AnnualFee,
        on_delete=models.PROTECT,
        related_name='invoice',
    )
    invoice_number = models.CharField(
        max_length=20,
        unique=True,
        default=generate_invoice_number,
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='invoices/', blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.invoice_number

    def generate_pdf(self):
        from django.template.loader import render_to_string
        from weasyprint import HTML

        html_string = render_to_string('fees/invoice_pdf.html', {'invoice': self})
        html = HTML(string=html_string, base_url=str(settings.BASE_DIR))
        filename = f'{self.invoice_number}.pdf'
        filepath = os.path.join(str(settings.MEDIA_ROOT), 'invoices', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        html.write_pdf(filepath)
        self.pdf_file = f'invoices/{filename}'
        self.save(update_fields=['pdf_file'])
