from django.conf import settings
from django.core.mail import send_mail


def send_invitation_email(invitation, onboarding_url):
    subject = '技擊跆拳道會 — 會員登記邀請 Member Registration Invitation'
    message = (
        f'您好，\n\n'
        f'{invitation.target_dojo.name} 邀請您為子女完成會員登記。\n'
        f'請按以下連結填寫資料（連結將於 {invitation.expires_at:%Y-%m-%d} 失效）：\n\n'
        f'{onboarding_url}\n\n'
        f'技擊跆拳道會 Advanced Taekwondo Club'
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[invitation.contact_email],
        fail_silently=False,
    )
