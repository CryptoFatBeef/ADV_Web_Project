from django.conf import settings
from django.core.files import File
from django.db import models


class PaymentMethod(models.TextChoices):
    STRIPE = 'STRIPE', 'Stripe'
    FPS_PAYME = 'FPS_PAYME', 'FPS / PayMe'


class PaymentStatus(models.TextChoices):
    PENDING_QR = 'PENDING_QR', 'Pending QR'
    SCREENSHOT_UPLOADED = 'SCREENSHOT_UPLOADED', 'Screenshot Uploaded'
    EMAIL_MATCHED = 'EMAIL_MATCHED', 'Email Matched'
    MANUALLY_CONFIRMED = 'MANUALLY_CONFIRMED', 'Manually Confirmed'
    FAILED = 'FAILED', 'Failed'
    REFUNDED = 'REFUNDED', 'Refunded'


class PaymentRecord(models.Model):
    annual_fee = models.ForeignKey(
        'fees.AnnualFee',
        on_delete=models.PROTECT,
        related_name='payment_records',
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_payments',
    )
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=25,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING_QR,
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default='HKD')
    # Stripe PaymentIntent ID or FPS reference number
    reference_id = models.CharField(max_length=200, blank=True)
    # Dev: stored in public MEDIA_ROOT; move to PRIVATE_STORAGE_ROOT in production
    screenshot = models.ImageField(upload_to='payment_screenshots/', blank=True)
    email_matched_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment #{self.pk} — {self.get_method_display()} [{self.get_status_display()}]'


class FPSQRCode(models.Model):
    payment_record = models.OneToOneField(
        PaymentRecord,
        on_delete=models.CASCADE,
        related_name='fps_qr',
    )
    # Dev: stored in public MEDIA_ROOT; move to PRIVATE_STORAGE_ROOT in production
    qr_image = models.ImageField(upload_to='fps_qr/', blank=True)
    merchant_name = models.CharField(max_length=200)
    fps_id = models.CharField(max_length=100)
    # Snapshot of amount at QR generation time — independent of PaymentRecord.amount
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f'FPS QR — {self.payment_record}'

    def generate_qr(self):
        import qrcode
        from io import BytesIO

        def tlv(tag, value):
            return f'{tag}{len(value):02d}{value}'

        # EMVCo Merchant-Presented QR — FPS Hong Kong merchant account info (tag 26)
        fps_account = tlv('00', 'hk.fps') + tlv('01', self.fps_id)
        merchant_name = self.merchant_name[:25]  # EMVCo spec: max 25 chars
        amount_str = f'{self.amount:.2f}'

        payload_body = (
            tlv('00', '01')              # payload format indicator
            + tlv('01', '12')            # point of initiation: dynamic (amount embedded)
            + tlv('26', fps_account)     # merchant account info — FPS
            + tlv('52', '0000')          # merchant category code: general
            + tlv('53', '344')           # transaction currency: HKD (ISO 4217)
            + tlv('54', amount_str)      # transaction amount
            + tlv('58', 'HK')            # country code
            + tlv('59', merchant_name)   # merchant name
            + tlv('60', 'Hong Kong')     # merchant city
            + '6304'                     # CRC tag + length placeholder
        )

        # HKMA FPS QR Code Specification v1.x, Section 4.11 — CRC-16/CCITT-FALSE
        # Polynomial: 0x1021, Init: 0xFFFF, no input/output reflection
        # TODO: validate against an official HKMA/FPS test vector before production
        crc = 0xFFFF
        for byte in payload_body.encode('utf-8'):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF

        full_payload = payload_body + f'{crc:04X}'

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(full_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        filename = f'fps_{self.payment_record.pk}.png'
        self.qr_image.save(filename, File(buffer), save=True)
