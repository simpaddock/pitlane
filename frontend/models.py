from django.db import models
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models.functions import Cast
from django.db import transaction
from pitlane.settings import LEAGUECONFIG, TEXTBLOCKCONTEXT
import re
from django.utils.html import mark_safe
from django.core.exceptions import ValidationError
import random
import string
from django.utils.html import strip_tags
from datetime import datetime
from os import unlink
from os.path import isfile
from frontend.resultcalculation import calculateRFactorResult
class Country(models.Model):
  name = models.CharField(max_length=100)
  flag = models.FileField(default=None, blank=True, upload_to='uploads/flags/')
  def __str__(self):
    return self.name

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
  def __str__(self):
    return "{0}".format(self.title)
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

class Registration(models.Model):
  email =models.EmailField(max_length=200, default="")
  number =models.IntegerField()
  teamName =models.CharField(blank=False, max_length=200, default="")
  skinFile = models.FileField(default=None, blank=True, upload_to='uploads/registration/',verbose_name="Skin file")
  season = models.ForeignKey(Season, on_delete=models.CASCADE, default=None)
  wasUploaded = models.BooleanField(default=False, blank=False)
  gdprAccept = models.BooleanField(default=False, blank=False, verbose_name="I consent the GDPR compilant processing of my submission data")
  copyrightAccept = models.BooleanField(default=False, blank=False, verbose_name="Our submission is free of copyright violations.")
  token = models.CharField(max_length=10, default="",blank=True)
  ignoreReason = RichTextUploadingField(default="", blank=True)
  def __str__(self):
    return "#" + str(self.number) + ": " + self.season.name + " (" + self.email + ") on Server: " + str(self.wasUploaded)
  @property
  def downloadLink(self):
    return mark_safe("""<a target="blank" href="{}">Download skin file</a>""".format(self.skinFile.url)) 
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
    if self.token =="":
      self.token = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
  def save(self, *args, **kwargs):
    super(Registration, self).save(*args, **kwargs)
    states = RegistrationStatus.objects.filter(registration=self).order_by("date")
    if states.count() == 0: # initial submission
      newStatus = RegistrationStatus()
      newStatus.registration = self
      newStatus.text = "We received your submission of car #{0} for season {1}. Filename: <a target=\"blank\" href=\"/media/{2}\">{2}</a>".format(self.number, self.season, self.skinFile) 
      newStatus.save()
    else:
      if self.ignoreReason != "":
        newStatus = RegistrationStatus()
        newStatus.registration = self
        newStatus.text = "Your submission for car #{0} will be ignored. Reason: {1}".format(self.number, self.ignoreReason)
        newStatus.save()
      else:
        newStatus = RegistrationStatus()
        newStatus.registration = self
        newStatus.text = "Your submission state changed. Car #{0}, on Server: {1}".format(self.number, self.wasUploaded)
        if self.wasUploaded:
          newStatus.text = newStatus.text + ". You can consider your submission as finished."
        newStatus.save()
    


class RegistrationStatus(models.Model):
  registration = models.ForeignKey(Registration, on_delete=models.CASCADE, default=None, related_name="Registration")
  text = models.TextField(max_length=500, blank=False, null=False)
  date = models.DateTimeField(default=datetime.now)
  def __str__(self):
    return "{0}: {1}".format(self.date.strftime(LEAGUECONFIG["dateFormat"]), self.text)

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
  driver = models.ForeignKey(Driver, on_delete=models.CASCADE, default=None)
  season = models.ForeignKey(Season, on_delete=models.CASCADE, default=None)
  ipAddress = models.GenericIPAddressField()
  def __str__(self):
    return self.season.name + ": " + str(self.driver)