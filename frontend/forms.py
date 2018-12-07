from django import forms
from .models import Registration, Incident, Race, Season, DriverEntry, GenericPrivacyAccept, DriverOfTheDayVote, Driver

class RegistrationForm(forms.ModelForm): 
  class Meta:
    model = Registration
    fields = ['email', 'teamName', 'skinFile', 'number', 'season', 'token', 'gdprAccept', 'copyrightAccept']
  def __init__(self, *args, **kwargs):
    super(RegistrationForm, self).__init__(*args, **kwargs)
    if self.instance:
        self.fields['season'].queryset = Season.objects.filter(isRunning=True,isOpen=True)

class GenericPrivacyAcceptAcceptForm(forms.ModelForm): 
  class Meta:
    model = GenericPrivacyAccept
    fields = ['email', 'givenName', 'familyName', 'privacyAccept']
  def __init__(self, *args, **kwargs):
    super(GenericPrivacyAcceptAcceptForm, self).__init__(*args, **kwargs)

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

class DriverOfTheDayVoteForm(forms.ModelForm): 
  class Meta:
    model = DriverOfTheDayVote
    fields = ('driver',)
  def __init__(self, *args, **kwargs):
    super(DriverOfTheDayVoteForm, self).__init__(*args, **kwargs)
    self.fields['driver'].queryset =  DriverEntry.objects.filter(teamEntry__season__driverOfTheDayVote=True).order_by("driver__lastName", "driver__firstName")
