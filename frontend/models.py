from django.db import models
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models.functions import Cast
from django.db import transaction
from pitlane.settings import LEAGUECONFIG, TEXTBLOCKCONTEXT, TEXTBLOCKOPTIONS
import re
from django.utils.html import mark_safe
from django.core.exceptions import ValidationError
import random
import string
from django.utils.html import strip_tags
from datetime import datetime
from os import unlink
from os.path import isfile
from nameparser import HumanName
from xml.dom import minidom

class Country(models.Model):
  name = models.CharField(max_length=100)
  flag = models.FileField(default=None, blank=True, upload_to='uploads/flags/')
  def __str__(self):
    return self.flag.url

class Track(models.Model):
  name = models.CharField(max_length=100)
  country = models.ForeignKey(Country, on_delete=models.CASCADE, default=None)
  long = models.FloatField(null=True, default=5)
  lat = models.FloatField(null=True, default=5)
  def __str__(self):
    return self.name

class Season(models.Model):
  name = models.CharField(max_length=100)
  isRunning = models.BooleanField(default=True)
  isOpen = models.BooleanField(default=True)
  driverOfTheDayVote = models.BooleanField(default=False, blank=False, verbose_name="Driver of the day vote")
  def __str__(self):
    return self.name
  @property
  def round(self):
    return RaceResult.objects.filter(race__season=self.pk).count()

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
  country = models.ForeignKey(Country, on_delete=models.CASCADE, default=None)
  image = models.FileField(default='logo.png', blank=True, upload_to='uploads/drivers/')
  def __str__(self):
    return "{0}, {1}".format(self.lastName, self.firstName)

class TeamEntry(models.Model):
  team = models.ForeignKey(Team, on_delete=models.CASCADE, default=None)
  season = models.ForeignKey(Season, on_delete=models.CASCADE, default=None)
  vehicle = models.CharField(null=True, default=None, max_length=100)
  vehicleImage = models.FileField(default=None, null=True, blank=True, upload_to='uploads/vehicles')
  def __str__(self):
    return "{0}@{1}: {2}".format(self.team.name, self.season.name, self.vehicle)

class Race(models.Model):
  season = models.ForeignKey(Season, on_delete=models.CASCADE, default=None)
  name = models.CharField(max_length=100)
  startDate = models.DateTimeField()
  endDate = models.DateTimeField()
  track = models.ForeignKey (Track, on_delete=models.CASCADE, default=None)
  streamLink = models.CharField(max_length=200, default=None, blank=True,null=True)
  commentatorInfo = models.CharField(max_length=200, default=None, blank=True,null=True)
  def __str__(self):
    return "{0}: {1}".format(self.season.name, self.name)
  @property
  def banner(self):
    return mark_safe("""<a target="blank" href="/racebanner/{}">Race Banner</a>""".format(self.id)) 

class RaceResult(models.Model):
  race = models.ForeignKey(Race, on_delete=models.CASCADE, default=None)
  resultFile = models.FileField(default=None, blank=True, upload_to='uploads/results/')
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
    return str(self.race.endDate) + ": " + self.race.name + " - " + self.race.season.name 
  @transaction.atomic
  def save(self, *args, **kwargs):
    super(RaceResult, self).save(*args, **kwargs)
    calculateRFactorResult(self, *args, **kwargs)

# see https://github.com/simpaddock/pitlane/issues/45
def calculateRFactorResult(self, *args, **kwargs):
    DriverRaceResultInfo.objects.filter(driverRaceResult__raceResult_id=self.id).delete()
    DriverRaceResult.objects.filter(raceResult_id=self.id).delete()

    filename = self.resultFile.path
    xml = minidom.parse(filename)

    trackLength = float(xml.getElementsByTagName('TrackLength')[0].childNodes[0].nodeValue)
    drivers = xml.getElementsByTagName('Driver')
    
    #precompute the max laps count over the complete grid
    maxLaps = 0
    for driver in drivers:
      runLaps = 0
      for node in driver.childNodes:
        if "Element" in str(type(node)):
          key = node.tagName
          if key == "Lap":
            runLaps  = runLaps + 1
      if runLaps > maxLaps:
        maxLaps = runLaps 
    
    for driver in drivers:
      rawData = {}
      runLaps = 0

      for node in driver.childNodes:
        if "Element" in str(type(node)):
          key = node.tagName
          print(key)
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
      if str(rawData["Position"]) in LEAGUECONFIG["ruleset"]["points"]:
        if runLaps > 0 and maxLaps > 0:
          percentage = 100/(maxLaps/runLaps)
        else:
          percentage = 0
        # i assume that the rfactor xml is sorted.
        if percentage > float(LEAGUECONFIG["ruleset"]["scoreLimit"]):
          rawData["Points"] = LEAGUECONFIG["ruleset"]["points"][str(rawData["Position"])]
        else:
          rawData["Points"]  = 0
      else:
        rawData["Points"] = 0

      # 1. Find Team
      teamName = rawData["TeamName"]
      carNumber = rawData["CarNumber"]
      vehicle = rawData["CarType"]
      
      fittingTeams = Team.objects.all().filter(name=teamName)
      if fittingTeams.count() == 0:
        # create new team
        newTeam = Team()
        newTeam.name = teamName
        newTeam.save()


      
      team = Team.objects.get(name=teamName) 
      
      if TeamEntry.objects.filter(season_id=self.race.season.id, team_id=team.id).count() == 0:
        # team is existing -> get new entry if needed
        newTeamEntry = TeamEntry()
        newTeamEntry.team = Team.objects.all().filter(name=teamName).get()
        newTeamEntry.vehicle = vehicle
        newTeamEntry.season = self.race.season
        newTeamEntry.save()

      teamEntry = TeamEntry.objects.filter(season_id=self.race.season.id, team=team).get()
      # 2. find Driver
      # concat name parts if the driver is e. g. a spanish speaking human
      name = HumanName(rawData["Name"])
      firstName = name.first
      if name.middle != "":
        lastName = name.middle + " " + name.last
      else:
        lastName = name.last
      fittingDrivers = Driver.objects.all().filter(firstName=firstName,lastName=lastName)

      driver=None
      if fittingDrivers.count() == 0:
        # create new driver
        driver = Driver()
        driver.firstName = firstName
        driver.lastName = lastName
        driver.country = Country.objects.first()
        driver.save()
        print("Created {0}, {1}".format(lastName, firstName))
      
      driver = Driver.objects.filter(firstName=firstName,lastName=lastName).get()
      if DriverEntry.objects.filter(driver_id=driver, teamEntry_id=teamEntry.id).count() == 0:
        # give the driver a new team entry 
        driverEntry = DriverEntry()
        driverEntry.driver = Driver.objects.filter(firstName=firstName,lastName=lastName).get()
        driverEntry.teamEntry = teamEntry
        driverEntry.driverNumber = carNumber
        driverEntry.driverNumberFormat = "{0}"
        driverEntry.save()
        print("--> New driver entry: {0} for {1}".format(carNumber, teamEntry))
        
      test =DriverEntry.objects.all()
      """
      I may run into a bug here. Django does not return anything useful with filter()
      """
      driverEntry = None
      for t in test:
        if t.driver == driver and t.teamEntry.season == self.race.season:
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
        "Points": "int",
        "CarType": "str"
      }
      for wantedKey in ["Stops", "Position", "FinishStatus", "Time","ControlAndAids", "Laps", "Points","CarType"]:
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

class DriverEntry(models.Model):
  driver = models.ForeignKey(Driver, on_delete=models.CASCADE, default=None)
  driverNumber = models.IntegerField()
  teamEntry = models.ForeignKey(TeamEntry, on_delete=models.CASCADE, default=None)
  driverNumberFormat = models.TextField()
  def __str__(self):
    return "#{0}: {1}, {2}: {3}".format(self.driverNumber, self.driver.lastName, self.driver.firstName, self.teamEntry.team.name)
    
  def clean(self):
    if DriverEntry.objects.filter(teamEntry__season=self.teamEntry.season, driverNumber=self.driverNumber).exclude(pk=self.id).count() != 0:
      raise ValidationError("An entry with that number already exists")


class DriverRaceResult(models.Model):
  raceResult = models.ForeignKey(RaceResult, on_delete=models.CASCADE, default=None)
  driverEntry = models.ForeignKey(DriverEntry, on_delete=models.CASCADE, default=None)
  @property
  def resultDetails(self):
    infos = DriverRaceResultInfo.objects.filter(driverRaceResult_id=self.id).order_by("name")
    resultDetailsHtml = ""
    for info in infos:
      resultDetailsHtml = resultDetailsHtml + "<a href='/admin/frontend/driverraceresultinfo/{0}/change/'>{1}</a><br>".format(info.id, str(info))
    return mark_safe(resultDetailsHtml) 
  def __str__(self):
    position = DriverRaceResultInfo.objects.filter(driverRaceResult_id=self.id, name="position").first()
    hasBonusPoints =  DriverRaceResultInfo.objects.filter(driverRaceResult_id=self.id, name="bonuspoints").count() > 0
    if position is None:
      return "{0} {1}@{2}".format(self.driverEntry.driver.firstName,self.driverEntry.driver.lastName, self.raceResult.race.name)
    if not hasBonusPoints:
      return "{0} {1}@{2} {3}.".format(self.driverEntry.driver.firstName,self.driverEntry.driver.lastName, self.raceResult.race.name,position.value)
    else:
      return "{0} {1}@{2} {3}. (Bonus points)".format(self.driverEntry.driver.firstName,self.driverEntry.driver.lastName, self.raceResult.race.name,position.value)

class DriverRaceResultInfo(models.Model):
  driverRaceResult = models.ForeignKey(DriverRaceResult, on_delete=models.CASCADE, default=None)
  name = models.CharField(max_length=100)
  value = models.CharField(max_length=100)
  infoType = models.CharField(max_length=100)
  def __str__(self):
    return self.name + ": " + str(self.value)

class NewsArticle(models.Model):
  title =models.CharField(max_length=200)
  text = RichTextUploadingField()
  date = models.DateTimeField()
  isDraft = models.BooleanField(default=False, blank=False, verbose_name="Is draft?")
  mediaFile = models.ImageField(default=None, blank=True, upload_to='uploads/news/')
  def __str__(self):
    return "{0}: {1}".format(self.date.strftime(LEAGUECONFIG["dateFormat"]), self.title)  
  def clean(self):
    if "script" in self.text.lower():
      raise ValidationError("Script tags are not allowed")



class Incident(models.Model):
  timeCode = models.FloatField()
  opponentCar = models.ForeignKey(DriverEntry, on_delete=models.CASCADE, default=None, related_name="opponent")
  ownCar =   models.ForeignKey(DriverEntry, on_delete=models.CASCADE, default=None)
  description =  models.TextField(default="", max_length=1000, verbose_name="Description")
  race = models.ForeignKey(Race, on_delete=models.CASCADE, default=None)
  result =  RichTextUploadingField(default="")
  def __str__(self):
    return "{0}: {1} vs {2}, decided: {3}".format(self.race.name, self.ownCar, self.opponentCar, len(self.result) > 0)

class TextBlock(models.Model):
  title = models.CharField(default="", max_length=100)
  text =  RichTextUploadingField()
  season = models.ForeignKey(Season, on_delete=models.CASCADE, blank=True, null=True)
  context = models.CharField(max_length=30,choices=TEXTBLOCKCONTEXT,default=TEXTBLOCKCONTEXT[0])
  mediaFile = models.ImageField(default=None, null=True,blank=True, upload_to='uploads/news/')
  orderIndex = models.IntegerField(default=0)
  options = models.CharField(max_length=30,choices=TEXTBLOCKOPTIONS,default=TEXTBLOCKOPTIONS[0])
  mediaFileThumbnail = models.BooleanField(default=False, blank=False)
  def __str__(self):
    return "{1}: {0} season: {2}".format(self.title, self.context, self.season)
  @property
  def plainText(self):
    return strip_tags(self.text.replace("\r",""))

class GenericPrivacyAccept(models.Model):
  email =models.EmailField(max_length=200, default="", verbose_name="Email address")
  givenName = models.CharField(blank=False, max_length=400, default="", verbose_name="Given name(s)")
  familyName = models.CharField(blank=False, max_length=400, default="", verbose_name="Family name")
  privacyAccept = models.BooleanField(default=False, blank=False, verbose_name="I give my consent")
  acceptDate = models.DateTimeField(default=datetime.now, blank=False)
  ipAddress = models.GenericIPAddressField()
  userAgent = models.CharField(blank=False, max_length=255, default="")
  def clean(self):
    if not self.privacyAccept:
      raise ValidationError("You need to accept.")
  def __str__(self):
    return "{0}, {1}".format(self.familyName, self.givenName)

class VehicleClass(models.Model):
  displayName = models.CharField(verbose_name="Vehicle display name", blank=False, max_length=300)
  vehicleClass = models.CharField(verbose_name="Internal name", max_length=300, blank=False)
  def __str__(self):
    return self.displayName

class Registration(models.Model):
  email =models.EmailField(max_length=200, default="")
  number =models.IntegerField(verbose_name="Car entry number")
  teamName =models.CharField(blank=False, max_length=200, default="", verbose_name="Team name")
  firstName = models.CharField(blank=False, max_length=200, default="", verbose_name = "Driver first name")
  lastName = models.CharField(blank=False, max_length=200, default="", verbose_name="Driver last name")
  season = models.ForeignKey(Season, on_delete=models.CASCADE, default=None)
  gdprAccept = models.BooleanField(default=False, blank=False, verbose_name="I consent the GDPR compilant processing of my submission data")
  token = models.CharField(max_length=10, default="",blank=True, verbose_name="Token (only needed if update)")
  vehicleClass = models.ForeignKey(VehicleClass, on_delete=models.CASCADE, default=None, blank=False, null=False, verbose_name="Vehicle")
  def __str__(self):
    return "#" + str(self.number) + ": " + self.season.name + " (" + self.email + ")"
    
  def clean(self):
    if not self.gdprAccept:
      raise ValidationError("You need to accept the GDPR that we can continue.")
    if not self.vehicleClass:
      raise ValidationError("Please choose your vehicle")

    numberGiven = Registration.objects.filter(number=self.number, season_id = self.season.id).count() > 0
    if numberGiven:
      otherCarWithThatNumber = Registration.objects.filter(number=self.number, season_id = self.season.id).first()
      if otherCarWithThatNumber.id != self.id: # dont do the validations when the id's are identical.
        if otherCarWithThatNumber.token != self.token:
          raise ValidationError("This number is given by another team")
        else:
          # update other entry
          # TODO: UPDATE OTHER ENTRY
          otherCarWithThatNumber.email = self.email
          otherCarWithThatNumber.number = self.number
          otherCarWithThatNumber.teamName = self.teamName
          otherCarWithThatNumber.firstName = self.firstName
          otherCarWithThatNumber.lastName = self.lastName
          otherCarWithThatNumber.season = self.season
          otherCarWithThatNumber.vehicleClass = self.vehicleClass
          otherCarWithThatNumber.save() 
          self.token = otherCarWithThatNumber.token
          raise ValidationError("The old registration was updated.")
    
    self.token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    
class LiverySubmission(models.Model):
  skinFile = models.FileField(default=None, blank=True, upload_to='uploads/registration/',verbose_name="Skin file")
  registrationToken = models.CharField(max_length=10, blank=False, null=False,verbose_name="Registration token")
  copyrightAccept = models.BooleanField(default=False, blank=False, verbose_name="Our submission is free of copyright violations.")
  
  @property
  def downloadLink(self):
    return mark_safe("""<a target="blank" href="{}">Download skin file</a>""".format(self.skinFile.url)) 
  
  @property
  def registrationLink(self):
    registration =  Registration.objects.filter(token=self.registrationToken).first()
    return mark_safe("""<a target="blank" href="/admin/frontend/registration/{}">{}</a>""".format(registration.id,registration)) 
  
  def clean(self):
    if Registration.objects.filter(token=self.registrationToken).count() == 0:
      raise ValidationError("Please check your registration token")
    if not self.copyrightAccept:
      raise ValidationError("Please make sure your skin is free of any copyright violation.")
    if self.skinFile and not self.skinFile.name.endswith(".dds"):
      raise ValidationError("The skin file must be .dds")
    LiverySubmission.objects.filter(registrationToken=self.registrationToken).delete()
  def __str__(self):
    return str(Registration.objects.filter(token=self.registrationToken).first())

    
class Upload(models.Model):
  name = models.CharField(default="", max_length=200,null=True)
  filePath = models.FileField(blank=True, default=None, null=True, upload_to='uploads/files')
  def delete(self):
    if self.filePath and isfile(self.filePath.path):
      unlink(self.filePath.path)
    super(Upload, self).delete()
  def __str__(self):
    return self.name

class DriverOfTheDayVote(models.Model):
  driver = models.ForeignKey(DriverEntry, on_delete=models.CASCADE, default=None)
  season = models.ForeignKey(Season, on_delete=models.CASCADE, default=None)
  ipAddress = models.GenericIPAddressField()
  def __str__(self):
    return self.season.name + ": " + str(self.driver)