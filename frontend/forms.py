from django import forms
from .models import Season, Team, TeamEntry
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