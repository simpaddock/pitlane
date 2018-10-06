from django.db import models
from ckeditor.fields import RichTextField
from pitlane.settings import LEAGUECONFIG, SIMSOFTWARE
from xml.dom import minidom
import re

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
  email = models.EmailField(default=None, null=True) # for managing..
  password = models.TextField(default=None, null=True) # for managing..
  logo = models.FileField(default=None, blank=True, upload_to='uploads/')

  def __str__(self):
    return self.name
  def logoUrl(self):
    if self.logo:
      return self.logo.url
    else:
      return None

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

class RaceOverlayControlSet(models.Model):
  race = models.ForeignKey(Race, on_delete=models.DO_NOTHING, default=None)
  controlSet = models.TextField() # Json, controls what to highlight currently
  slotId = models.IntegerField(default=1)
  cameraId = models.IntegerField(default=4)

class RaceResult(models.Model):
  race = models.ForeignKey(Race, on_delete=models.DO_NOTHING, default=None)
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  resultSoftware = models.CharField(max_length=30,choices=SIMSOFTWARE,default='rFactor 2')
  resultFile = models.FileField(default=None, blank=True, upload_to='uploads/')
  streamLink = models.CharField(max_length=200, default=None, blank=True,null=True)
  commentatorInfo = models.CharField(max_length=200, default=None, blank=True,null=True)
  def __str__(self):
    return str(self.race.endDate) + ": " + self.race.name + " - " + self.season.name 
  def save(self, *args, **kwargs):
    super(RaceResult, self).save(*args, **kwargs)
    filename = self.resultFile.path
    xml = minidom.parse(filename)

    trackLength = float(xml.getElementsByTagName('TrackLength')[0].childNodes[0].nodeValue)
    drivers = xml.getElementsByTagName('Driver')
    
    
    for driverRaceResult in DriverRaceResult.objects.filter(raceResult_id=self.id):
      DriverRaceResultInfo.objects.filter(driverRaceResult_id=driverRaceResult.id).delete()
      driverRaceResult.delete()
    maxLaps = 0
    for driver in drivers:
      rawData = {}
      runLaps = 0

      for node in driver.childNodes:
        if "Element" in str(type(node)):
          key = node.tagName
          if key == "Pitstops":
            key = "Stops"
          if key == "FinishTime":
            key = "Time"
          value = node.childNodes[0].nodeValue
          if key not in rawData:
            rawData[key] = value
          if key == "Lap":
            runLaps  = runLaps + 1

      rawData["Laps"] = runLaps
      pointMap = {
        1: 25,
        2: 18,
        3: 15,
        4: 12,
        5: 10,
        6: 8,
        7: 6,
        8: 4,
        9: 2,
        10: 1
      }
      if int(rawData["Position"]) in pointMap:
        if int(rawData["Position"]) == 1:
          maxLaps = runLaps
        if runLaps > 0 and maxLaps > 0:
          percentage = 100/(maxLaps/runLaps)
        else:
          percentage = 0
        # i assume that the rfactor xml is sorted.
        if percentage > 90:
          rawData["Points"] = pointMap[int(rawData["Position"])]
        else:
          rawData["Points"]  = 0
      else:
        rawData["Points"] = 0

      # 1. Find Team
      teamCarParts = rawData["VehName"].split("#")
      teamName = teamCarParts[0].strip(" ")
      carNumber = teamCarParts[1]
      vehicle = rawData["CarClass"]
      
      fittingTeams = Team.objects.all().filter(name=teamName)
      if fittingTeams.count() == 0:
        # create new team
        newTeam = Team()
        newTeam.name = teamName
        newTeam.save()
        # create season entry
        newTeamEntry = TeamEntry()
        newTeamEntry.team = newTeam
        newTeamEntry.vehicle = vehicle
        newTeamEntry.season = self.season
        newTeamEntry.save()
      
      team = Team.objects.get(name=teamName)
      teamEntry = TeamEntry.objects.get(team=team)

      # 2. find Driver
      nameParts = rawData["Name"].split(" ")
      firstName = nameParts[0]
      lastName = nameParts[1]
      fittingDrivers = Driver.objects.all().filter(firstName=firstName).filter(lastName=lastName)
      if fittingDrivers.count() == 0:
        # create new driver
        driver = Driver()
        driver.firstName = firstName
        driver.lastName = lastName
        driver.country = Country.objects.first()
        driver.save()

        driverEntry = DriverEntry()
        driverEntry.driver = driver
        driverEntry.teamEntry = teamEntry
        driverEntry.driverNumber = carNumber
        driverEntry.driverNumberFormat = "{0}"
        driverEntry.save()
      
      driver = Driver.objects.all().filter(firstName=firstName).filter(lastName=lastName).get()
      driverEntry = DriverEntry.objects.get(driver=driver, teamEntry=teamEntry)
      # remove old ones
      

      driverRaceResult = DriverRaceResult()
      driverRaceResult.driverEntry = driverEntry
      driverRaceResult.raceResult =  self
      driverRaceResult.save()
      keyTypes = {
        "Stops": "int",
        "Position": "position",
        "FinishStatus": "status",
        "Time": "str",
        "ControlAndAids": "str",
        "Laps": "int",
        "Points": "int"
      }
      for wantedKey in ["Stops", "Position", "FinishStatus", "Time","ControlAndAids", "Laps", "Points"]:
        if wantedKey in rawData:
          driverRaceResultInfo = DriverRaceResultInfo()
          driverRaceResultInfo.driverRaceResult = driverRaceResult
          driverRaceResultInfo.name = wantedKey.lower()
          if wantedKey == "ControlAndAids":
            driverRaceResultInfo.value = rawData[wantedKey].replace("PlayerControl,","")
          else:
            driverRaceResultInfo.value = rawData[wantedKey]
          driverRaceResultInfo.infoType = "str"
          driverRaceResultInfo.save()
      if "Time" in rawData:
        # create additional result infos
        driverRaceResultInfo = DriverRaceResultInfo()
        driverRaceResultInfo.driverRaceResult = driverRaceResult
        driverRaceResultInfo.name = "avg"
        driverRaceResultInfo.value = round(((trackLength/1000)*runLaps)/ (float(rawData["Time"])/60/60),2)
        driverRaceResultInfo.infoType = "str"
        driverRaceResultInfo.save()

    # parse the xml input file
    # todo: put into separate file


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