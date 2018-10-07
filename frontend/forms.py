from django import forms
from .models import Registration

class RegistrationForm(forms.ModelForm): 
  class Meta:
    model = Registration
    fields = ['email', 'skinFile', 'number', 'season', 'token', 'gdprAccept', 'copyrightAccept']

