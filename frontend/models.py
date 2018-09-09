from django.db import models
from ckeditor.fields import RichTextField
from pitlane.settings import LEAGUECONFIG

class Country(models.Model):
  name = models.CharField(max_length=100)
  flag = models.FileField(default=None, blank=True, upload_to='uploads/')
  def __str__(self):
    return self.name

class Track(models.Model):
  name = models.CharField(max_length=100)
  country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, default=None)
  long = models.FloatField(null=True, default=5)
  lat = models.FloatField(null=True, default=5)
  def __str__(self):
    return self.name

class Season(models.Model):
  name = models.CharField(max_length=100)
  isRunning = models.BooleanField(default=True)
  def __str__(self):
    return self.name

class Team(models.Model):
  name = models.CharField(max_length=100)
  logo = models.FileField(default=None, blank=True, upload_to='uploads/')
  def __str__(self):
    return self.name

class Driver(models.Model):
  firstName = models.CharField(max_length=100)
  lastName = models.CharField(max_length=100)
  country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, default=None)
  image = models.FileField(default='logo.png', blank=True, upload_to='uploads/')
  def __str__(self):
    return "{0}, {1} ({2})".format(self.lastName, self.firstName, self.country.name)

class TeamEntry(models.Model):
  team = models.ForeignKey(Team, on_delete=models.DO_NOTHING, default=None)
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  vehicle = models.CharField(null=True, default=None, max_length=100)
  def __str__(self):
    return "{0}@{1}: {2}".format(self.team.name, self.season.name, self.vehicle)

class Race(models.Model):
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  name = models.CharField(max_length=100)
  startDate = models.DateTimeField()
  endDate = models.DateTimeField()
  track = models.ForeignKey (Track, on_delete=models.DO_NOTHING, default=None)
  def __str__(self):
    return "{0}: {1} in {2}".format(self.startDate, self.name, self.track)

class RaceResult(models.Model):
  race = models.ForeignKey(Race, on_delete=models.DO_NOTHING, default=None)
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  def __str__(self):
    return str(self.race.endDate) + ": " + self.race.name + " - " + self.season.name 

class DriverEntry(models.Model):
  driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, default=None)
  driverNumber = models.IntegerField()
  teamEntry = models.ForeignKey(TeamEntry, on_delete=models.DO_NOTHING, default=None)
  driverNumberFormat = RichTextField()
  def __str__(self):
    return "#{0}: {1}, {2}: {3}".format(self.driverNumber, self.driver.lastName, self.driver.firstName, self.teamEntry.team.name)

class DriverRaceResult(models.Model):
  raceResult = models.ForeignKey(RaceResult, on_delete=models.DO_NOTHING, default=None)
  driverEntry = models.ForeignKey(DriverEntry, on_delete=models.DO_NOTHING, default=None)
  def __str__(self):
    return self.driverEntry.driver.lastName

class DriverRaceResultInfo(models.Model):
  driverRaceResult = models.ForeignKey(DriverRaceResult, on_delete=models.DO_NOTHING, default=None)
  name = models.CharField(max_length=100)
  value = models.CharField(max_length=100)
  infoType = models.CharField(max_length=100)
  def __str__(self):
    return self.name + ":" + str(self.value)

class NewsArticle(models.Model):
  title =models.CharField(max_length=200)
  text = RichTextField()
  date = models.DateTimeField()
  mediaFile = models.FileField(default=None, blank=True, upload_to='uploads/')
  def __str__(self):
    return "{0}: {1}".format(self.date.strftime(LEAGUECONFIG["dateFormat"]), self.title)