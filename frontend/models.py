from django.db import models

class Country(models.Model):
  name = models.TextField(max_length=100)
  flag = models.TextField(max_length=100)

class Track(models.Model):
  name = models.TextField(max_length=100)
  country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, default=None)
  long = models.FloatField(null=True, default=5)
  lat = models.FloatField(null=True, default=5)


class Season(models.Model):
  name = models.TextField(max_length=100)
  isRunning = models.BooleanField(default=True)

class Team(models.Model):
  name = models.TextField(max_length=100)
  logo = models.TextField(max_length=100)

class Driver(models.Model):
  firstName = models.TextField()
  lastName = models.TextField()
  country = models.ForeignKey(Country, on_delete=models.DO_NOTHING, default=None)
  image = models.TextField(default='driver.png')

class TeamEntry(models.Model):
  team = models.ForeignKey(Team, on_delete=models.DO_NOTHING, default=None)
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  vehicle = models.TextField(null=True, default=None)

class Race(models.Model):
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  name = models.TextField(max_length=100)
  startDate = models.DateTimeField()
  endDate = models.DateTimeField()
  track = models.ForeignKey (Track, on_delete=models.DO_NOTHING, default=None)

class RaceResult(models.Model):
  race = models.ForeignKey(Race, on_delete=models.DO_NOTHING, default=None)
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)

class DriverEntry(models.Model):
  driver = models.ForeignKey(Driver, on_delete=models.DO_NOTHING, default=None)
  driverNumber = models.IntegerField()
  teamEntry = models.ForeignKey(TeamEntry, on_delete=models.DO_NOTHING, default=None)
  driverNumberFormat = models.TextField()

class DriverRaceResult(models.Model):
  raceResult = models.ForeignKey(RaceResult, on_delete=models.DO_NOTHING, default=None)
  driverEntry = models.ForeignKey(DriverEntry, on_delete=models.DO_NOTHING, default=None)
  def __str__(self):
    return self.driverEntry.driver.lastName

class DriverRaceResultInfo(models.Model):
  driverRaceResult = models.ForeignKey(DriverRaceResult, on_delete=models.DO_NOTHING, default=None)
  name = models.TextField()
  value = models.TextField()
  infoType = models.TextField()
  def __str__(self):
    return self.name + ":" + str(self.value)

class NewsArticle(models.Model):
  title = models.TextField()
  text = models.TextField()
  date = models.DateTimeField()
  mediaFile = models.FileField(default=None, blank=True, upload_to='uploads/')