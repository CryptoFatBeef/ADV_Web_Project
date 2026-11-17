from django import forms
from django.contrib.auth import get_user_model

from .models import GuardianRelationship, MemberProfile, RegistrationInvitation

User = get_user_model()


class MemberContactForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = [
            'chinese_name', 'date_of_birth', 'gender', 'height_cm', 'weight_kg',
            'emergency_contact_name', 'emergency_contact_phone',
            'current_belt', 'tier', 'status', 'primary_dojo',
            'public_showcase_consent', 'notes',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'public_showcase_consent':
                field.widget.attrs['class'] = 'form-control'


class InvitationRequestForm(forms.ModelForm):
    class Meta:
        model = RegistrationInvitation
        fields = ['contact_email', 'target_dojo']

    def __init__(self, *args, dojo_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if dojo_queryset is not None:
            self.fields['target_dojo'].queryset = dojo_queryset
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class OnboardingForm(forms.Form):
    guardian_first_name = forms.CharField(max_length=150, label='監護人 English First Name')
    guardian_last_name = forms.CharField(max_length=150, label='監護人 English Last Name')
    guardian_phone = forms.CharField(max_length=30, label='監護人聯絡電話')
    relationship = forms.ChoiceField(choices=GuardianRelationship.choices, label='與會員關係')
    password = forms.CharField(widget=forms.PasswordInput, label='設定登入密碼', min_length=8)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='確認密碼')

    member_first_name = forms.CharField(max_length=150, label='會員 English First Name')
    member_last_name = forms.CharField(max_length=150, label='會員 English Last Name')
    member_chinese_name = forms.CharField(max_length=100, required=False, label='會員中文姓名')
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='出生日期')
    gender = forms.ChoiceField(choices=MemberProfile.Gender.choices, label='性別')
    height_cm = forms.DecimalField(max_digits=5, decimal_places=1, required=False, label='身高 (cm)')
    weight_kg = forms.DecimalField(max_digits=5, decimal_places=1, required=False, label='體重 (kg)')
    emergency_contact_name = forms.CharField(max_length=150, label='緊急聯絡人')
    emergency_contact_phone = forms.CharField(max_length=30, label='緊急聯絡電話')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('密碼與確認密碼不相符 / Passwords do not match.')
        return cleaned_data
