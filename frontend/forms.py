from django import forms
from .models import Registration, Incident, Race, Season, DriverEntry

class RegistrationForm(forms.ModelForm): 
  class Meta:
    model = Registration
    fields = ['email', 'skinFile', 'number', 'season', 'token', 'gdprAccept', 'copyrightAccept']
  def __init__(self, *args, **kwargs):
      super(RegistrationForm, self).__init__(*args, **kwargs)
      if self.instance:
          self.fields['season'].queryset = Season.objects.filter(isRunning=True)

class IncidentForm(forms.ModelForm): 
  class Meta:
    model = Incident
    fields = '__all__'
    exclude = ('result',)
  def __init__(self, *args, **kwargs):
      super(IncidentForm, self).__init__(*args, **kwargs)
      if self.instance:
          self.fields['race'].queryset = Race.objects.filter(season__isRunning=True)
          self.fields['ownCar'].queryset = DriverEntry.objects.filter(teamEntry__season__isRunning=True)
          self.fields['opponentCar'].queryset = self.fields['ownCar'].queryset
