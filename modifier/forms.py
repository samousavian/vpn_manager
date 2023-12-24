from django import forms
from datetime import datetime, timedelta


class UpdateInboundFrom(forms.Form):
    days = forms.IntegerField(
        label="Days",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    traffic = forms.IntegerField(
        label="Traffic",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )


class AddInboundForm(forms.Form):
    PROTOCOL_CHOICES = [
        ('vmess', 'vmess-tcp-tls'),
        ('vless', 'vless-tcp-xtls'),
        ('trojan', 'trojan-tcp-xtls')
    ]

    server_name = forms.ChoiceField(
        label="Server Name",
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    remark = forms.CharField(
        label="Remark",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    total = forms.IntegerField(
        label="Total",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    days = forms.IntegerField(
        label="Days",
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    protocol = forms.ChoiceField(
        label="Protocol",
        choices=PROTOCOL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        # Get the server_name_choices from kwargs and update the choices for server_name field
        server_name_choices = kwargs.pop('server_name_choices', [])
        super(AddInboundForm, self).__init__(*args, **kwargs)
        self.fields['server_name'].choices = server_name_choices
