from django import forms
from .models import Season, Team, TeamEntry, DriverEntry, Driver,Country

class DriverSignUpForm(forms.Form):
  firstName = forms.CharField(max_length=30)
  lastName = forms.CharField(max_length=30)
  number = forms.IntegerField()
  numberFormat = forms.CharField(max_length=100, initial="{0}")
  teamEntry = forms.ModelChoiceField(queryset = TeamEntry.objects.all(),empty_label="(Nothing)")
  password = forms.CharField(widget=forms.PasswordInput())
  def clean(self):
    super().clean()
    driver = Driver()
    driver.firstName = self.cleaned_data["firstName"]
    driver.lastName = self.cleaned_data["lastName"]
    driver.country = Country.objects.first()
    driver.save()

    driverEntry = DriverEntry()
    driverEntry.teamEntry = self.cleaned_data["teamEntry"]
    driverEntry.driverNumber = self.cleaned_data["number"]
    driverEntry.driverNumberFormat = self.cleaned_data["numberFormat"]
    driverEntry.driver = driver
    driverEntry.save()
    print(self.cleaned_data)



class TeamSignUpForm(forms.Form):
  name = forms.CharField(max_length=30)
  email = forms.EmailField(max_length=254)
  season = forms.ModelChoiceField(queryset = Season.objects.all(),empty_label="(Nothing)")
  vehicle = forms.CharField(max_length=30)
  logo = forms.FileField()
  password = forms.CharField(widget=forms.PasswordInput())

  def clean(self):
    
    super().clean()
    # search if a team is existing in that season
    teams = Team.objects.filter(name =self.cleaned_data["name"] ) | Team.objects.filter(email =self.cleaned_data["email"] )
    if teams.count() == 0:
      # create new team entry
      team = Team()
      team.name = self.cleaned_data["name"]
      team.email = self.cleaned_data["email"]
      team.logo = self.files["logo"]
      team.password = self.cleaned_data["password"]
      team.save()

      teamEntry = TeamEntry()
      teamEntry.season = self.cleaned_data["season"]
      teamEntry.team = team
      teamEntry.save()
    else:
      print("fasjklfas")
    # create team and entry entry