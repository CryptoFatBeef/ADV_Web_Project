from django import forms

from apps.enrollment.models import EnrollmentLead


class EnrollmentLeadForm(forms.ModelForm):
    consent_pdpo = forms.BooleanField(
        required=True,
        label='我同意本會根據《個人資料（私隱）條例》收集及使用以上個人資料，作報名及聯絡用途。',
        error_messages={'required': '請確認同意私隱政策方可提交表格。'},
    )

    class Meta:
        model = EnrollmentLead
        fields = [
            'full_name', 'contact_phone', 'contact_email',
            'interested_dojo', 'child_age', 'message', 'consent_pdpo',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'consent_pdpo':
                field.widget.attrs['class'] = 'form-control'

    def clean_consent_pdpo(self):
        consent = self.cleaned_data.get('consent_pdpo')
        if not consent:
            raise forms.ValidationError('請確認同意私隱政策方可提交表格。')
        return consent
