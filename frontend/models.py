from django.db import models
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models.functions import Cast
from pitlane.settings import LEAGUECONFIG, SIMSOFTWARE, TEXTBLOCKCONTEXT
from xml.dom import minidom
import re
from django.utils.html import mark_safe
from django.core.exceptions import ValidationError
import random
import string
from django.utils.html import strip_tags
class Country(models.Model):
  name = models.CharField(max_length=100)
  flag = models.FileField(default=None, blank=True, upload_to='uploads/flags/')
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
  logo = models.FileField(default=None, blank=True, upload_to='uploads/teams/')

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
  image = models.FileField(default='logo.png', blank=True, upload_to='uploads/drivers/')
  def __str__(self):
    return "{0}, {1} ({2})".format(self.lastName, self.firstName, self.country.name)

class TeamEntry(models.Model):
  team = models.ForeignKey(Team, on_delete=models.DO_NOTHING, default=None)
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  vehicle = models.CharField(null=True, default=None, max_length=100)
  vehicleImage = models.FileField(default=None, null=True, blank=True, upload_to='uploads/vehicles')
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
  resultFile = models.FileField(default=None, blank=True, upload_to='uploads/results/')
  streamLink = models.CharField(max_length=200, default=None, blank=True,null=True)
  commentatorInfo = models.CharField(max_length=200, default=None, blank=True,null=True)
  @property
  def results(self):
    if self.resultFile is not None:
      resultText = ""
      positions = DriverRaceResultInfo.objects.filter(driverRaceResult__raceResult_id=self.id).annotate(
        intPosition=Cast('value', models.IntegerField())
      ).filter(name="position").order_by("intPosition")
      for position in positions:
        driverRaceResult = position.driverRaceResult
        resultText = "{0}{1}. {2} {3}\n".format(resultText, position.value, driverRaceResult.driverEntry.driver.firstName, driverRaceResult.driverEntry.driver.lastName)
        print(driverRaceResult)
      return resultText
    return ""
  def __str__(self):
    return str(self.race.endDate) + ": " + self.race.name + " - " + self.season.name 
  def save(self, *args, **kwargs):
    super(RaceResult, self).save(*args, **kwargs)

    
    # cleanup old data
    DriverRaceResultInfo.objects.filter(driverRaceResult__raceResult_id=self.id).delete()
    DriverRaceResult.objects.filter(raceResult_id=self.id).delete()

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
        if percentage > 70:
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


      
      team = Team.objects.get(name=teamName) 
      
      if TeamEntry.objects.filter(season_id=self.season.id, team_id=team.id).count() == 0:
        # team is existing -> get new entry if needed
        newTeamEntry = TeamEntry()
        newTeamEntry.team = Team.objects.all().filter(name=teamName).get()
        newTeamEntry.vehicle = vehicle
        newTeamEntry.season = self.season
        newTeamEntry.save()

      teamEntry = TeamEntry.objects.filter(season_id=self.season.id, team=team).get()
      # 2. find Driver
      nameParts = rawData["Name"].split(" ")
      firstName = nameParts[0]
      lastName = nameParts[1]
      fittingDrivers = Driver.objects.all().filter(firstName=firstName,lastName=lastName)
      driver=None
      if fittingDrivers.count() == 0:
        # create new driver
        driver = Driver()
        driver.firstName = firstName
        driver.lastName = lastName
        driver.country = Country.objects.first()
        driver.save()
      
      driver = Driver.objects.filter(firstName=firstName,lastName=lastName).get()
      if DriverEntry.objects.filter(driver_id=driver, teamEntry_id=teamEntry.id).count() == 0:
        # give the driver a new team entry 
        driverEntry = DriverEntry()
        driverEntry.driver = Driver.objects.filter(firstName=firstName,lastName=lastName).get()
        driverEntry.teamEntry = teamEntry
        driverEntry.driverNumber = carNumber
        driverEntry.driverNumberFormat = "{0}"
        driverEntry.save()
      
      print(driver.id, driver, teamEntry)
      test =DriverEntry.objects.all()
      """
      I may run into a bug here. Django does not return anything useful with filter()
      """
      driverEntry = None
      for t in test:
        if t.driver == driver and t.teamEntry.season == self.season:
         driverEntry = t
         break

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
  def __str__(self):
    position = DriverRaceResultInfo.objects.filter(driverRaceResult_id=self.id, name="position").first()
    status = DriverRaceResultInfo.objects.filter(driverRaceResult_id=self.id, name="finishstatus").first()
    return "{0} {1}@{2} ({3}): {4}. ({5})".format(self.driverEntry.driver.firstName,self.driverEntry.driver.lastName, self.raceResult.race.name,  self.raceResult.race.startDate, position.value, status.value)

class DriverRaceResultInfo(models.Model):
  driverRaceResult = models.ForeignKey(DriverRaceResult, on_delete=models.DO_NOTHING, default=None)
  name = models.CharField(max_length=100)
  value = models.CharField(max_length=100)
  infoType = models.CharField(max_length=100)
  def __str__(self):
    return self.name + ":" + str(self.value)

class NewsArticle(models.Model):
  title =models.CharField(max_length=200)
  text = RichTextUploadingField()
  date = models.DateTimeField()
  mediaFile = models.FileField(default=None, blank=True, upload_to='uploads/news/')
  def __str__(self):
    return "{0}: {1}".format(self.date.strftime(LEAGUECONFIG["dateFormat"]), self.title)

class Incident(models.Model):
  timeCode = models.FloatField()
  opponentCar = models.CharField(default="", max_length=100, verbose_name="Opponent car")
  ownCar =  models.CharField(default="", max_length=100, verbose_name="Own car")
  description =  models.TextField(default="", max_length=1000, verbose_name="Description")
  race = models.ForeignKey(Race, on_delete=models.DO_NOTHING, default=None)
  result =  models.TextField(default="", max_length=100)
  def __str__(self):
    return "{0}: {1} vs {1}: {2}".format(self.race.name, self.ownCar, self.opponentCar, self.result)

class TextBlock(models.Model):
  title = models.CharField(default="", max_length=100)
  text =  RichTextUploadingField()
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, blank=True, null=True)
  context = models.CharField(max_length=30,choices=TEXTBLOCKCONTEXT,default=TEXTBLOCKCONTEXT[0])
  def __str__(self):
    return "{0}".format(self.title)
  @property
  def plainText(self):
    return strip_tags(self.text.replace("\r",""))



class Registration(models.Model):
  email =models.EmailField(max_length=200, default="")
  number =models.IntegerField()
  skinFile = models.FileField(default=None, blank=False, upload_to='uploads/registration/',verbose_name="Skin file")
  season = models.ForeignKey(Season, on_delete=models.DO_NOTHING, default=None)
  wasUploaded = models.BooleanField(default=False, blank=False)
  gdprAccept = models.BooleanField(default=False, blank=False, verbose_name="I consent the GDPR compilant processing of my submission data")
  copyrightAccept = models.BooleanField(default=False, blank=False, verbose_name="Our submission is free of copyright violations.")
  token = models.CharField(max_length=10, default="",blank=True)
  def __str__(self):
    return "#" + str(self.number) + ": " + self.season.name + " (" + self.email + ") on Server: " + str(self.wasUploaded)
  @property
  def downloadLink(self):
    return mark_safe("""<a target="blank" href="/static/frontend/{}">Download skin file</a>""".format(self.skinFile.url)) 
  def clean(self):
    if not self.gdprAccept:
      raise ValidationError("You need to accept the GDPR that we can continue.")
    if not self.copyrightAccept:
      raise ValidationError("Please make sure your skin is free of any copyright violation.")

    numberGiven = Registration.objects.filter(number=self.number, season_id = self.season.id).count() > 0
    if numberGiven:
      otherCarWithThatNumber = Registration.objects.filter(number=self.number, season_id = self.season.id).first()
      if otherCarWithThatNumber.id != self.id: # dont do the validations when the id's are identical.
        if otherCarWithThatNumber.token != self.token:
          raise ValidationError("This number is given by another team")
        else:
          # update other entry
          otherCarWithThatNumber.skinFile = self.skinFile
          otherCarWithThatNumber.wasUploaded = False
          otherCarWithThatNumber.save()
          self.token = otherCarWithThatNumber.token
          raise ValidationError("The old registration was updated.")
    self.token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    

