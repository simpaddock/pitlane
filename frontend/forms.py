from django import forms
from .models import Registration, Incident

class RegistrationForm(forms.ModelForm): 
  class Meta:
    model = Registration
    fields = ['email', 'skinFile', 'number', 'season', 'token', 'gdprAccept', 'copyrightAccept']

class IncidentForm(forms.ModelForm): 
  class Meta:
    model = Incident
    fields = '__all__'
    exclude = ('result',)
