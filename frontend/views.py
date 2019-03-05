from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from collections import OrderedDict
from django.db import models
from django.http import Http404
from .models import Upload, TextBlock, NewsArticle, Season, Race, TeamEntry, Track, RaceResult, DriverRaceResult, DriverRaceResultInfo, DriverEntry, Driver, Team
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from json import dumps, loads
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import filetype
from functools import reduce
from .forms import *
from requests import get
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from pitlane.settings import STATIC_ROOT, LEAGUECONFIG, MEDIA_ROOT, COLUMNS, NUMBERGENERATOROFFSETS
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from icalendar import Calendar, Event
import pytz
from datetime import datetime, date, time
from urllib.parse import urljoin
import matplotlib
matplotlib.use("Agg")
import base64
from frontend.utils import generateSparkline, getChildValue, getSeasonDrivers, getRaceResult, getTeamStandings, getClientIP, JSONEncoder
from frontend.templatetags.frontend_tags import next_championship
LIST_DATA_RACE = "race"
LIST_DATA_TEAM_STANDINGS = "teams"
LIST_DATA_DRIVERS_STANDINGS = "drivers"
LIST_DATA_DRIVERS ="listdrivers"


from pitlane.settings import LEAGUECONFIG

def getRoutes():
  routes = OrderedDict()
  season = next_championship()
  routes["news"] = "News"
  routes["seasons"] = "Seasons"
  if season is not None:
    routes["seasons/"+str(season.id)+"/drivers"] = "Drivers"
    routes["seasons/"+str(season.id)+"/teams"] = "Teams"
  routes["about"] = "about"
  if LEAGUECONFIG["pitlane"] is not None:
    routes[LEAGUECONFIG["pitlane"]] = "Forum"
  routes["rules"] = "Rules"
  routes["incidentreport"] = "Incident report"
  return routes

def get_robots(request):
  text = "User-agent: *\n"
  for url in LEAGUECONFIG["robots"]["disallow"]:
    text = text + "Disallow: {0}{1}".format(url,"\n")
  return HttpResponse(text, content_type='text/plain')

def renderWithCommonData(request, template, context):
  context["routes"] = getRoutes()
  context["config"] = LEAGUECONFIG
  context["running"] = next_championship()
  template = template.replace("frontend/", "frontend/" + LEAGUECONFIG["theme"] + "/")
  context["baseLayout"] = 'frontend/'+  LEAGUECONFIG["theme"] + '/layout.html'
  return render(request, template, context)

def get_index(request):
  races = Race.objects.all().filter(season=next_championship()).order_by("startDate")
  newsArticles = NewsArticle.objects.filter(isDraft=False).order_by("-date")[:12]
  textBlocks = TextBlock.objects.filter(context='landing')
  return renderWithCommonData(request, 'frontend/index.html', {
    "events": races,
    "newsArticles": newsArticles,
    "textBlocks": textBlocks
  })

@cache_page(60 * 15)
def get_news(request):
  articles = NewsArticle.objects.filter(isDraft=False).order_by("-date")
  paginator = Paginator(articles, 50)
  page = request.GET.get('page')
  return renderWithCommonData(request, 'frontend/news.html', {
    "articles": paginator.get_page(page)
  })

@cache_page(60 * 15)
def get_about(request):
  name = LEAGUECONFIG["name"]
  logo = LEAGUECONFIG["logo"]
  textBlocks = TextBlock.objects.filter(context='about').order_by("orderIndex")
  return renderWithCommonData(request, 'frontend/about.html', {
    "name": name,
    "logo": logo,
    "textBlocks": textBlocks
  })

@cache_page(60 * 15)  
def get_rules(request):
  return renderWithCommonData(request, 'frontend/rules.html', {
    "rules": TextBlock.objects.filter(season__isRunning=True, context='rule').order_by("orderIndex")
  })

@cache_page(60 * 15)
def get_privacy(request):
  return renderWithCommonData(request, 'frontend/privacy.html', {})

@cache_page(60 * 15)
def get_imprint(request):
  return renderWithCommonData(request, 'frontend/imprint.html', {})

@cache_page(60 * 15)
def get_SingleNews(request, id:int):
  articles = list(NewsArticle.objects.all().filter(pk=id))
  paginator = Paginator(articles, 5)
  page = request.GET.get('page'),
  url = urljoin(LEAGUECONFIG["url"], '/news/'+ str(articles[0].id)) # ",/" does not work 
  title = articles[0].title
  return renderWithCommonData(request, 'frontend/article.html', {
    "articles": paginator.get_page(page),
    "title": title
  })



@cache_page(60 * 15)
def get_seasonList(request):
  seasonList = Season.objects.all().order_by("-isRunning")
  races = {}
  resultList = []
  for season in seasonList:
    obj = model_to_dict(season)
    obj["races"] = []
    obj["drivers"] =getSeasonDrivers(season.id)
    obj["teams"] = []
    for driver in obj["drivers"]:
      if driver.teamEntry.id not in obj["teams"]:
        obj["teams"].append(driver.teamEntry.id)
    
    seasonId = season.id
    # TODO: FIND A BETTER FUCKING WAY TO SERIALIZE
    for race in Race.objects.all().filter(season_id=seasonId).order_by("startDate"):
      raceObj = model_to_dict(race)
      track = Track.objects.all().filter(pk=raceObj["track"]).get()
      country = track.country
      raceObj["track"] = model_to_dict(track)
      raceObj["track"]["country"] = model_to_dict(country)
      obj["races"].append(raceObj)
    resultList.append(obj)
  
  seasonsJSON = dumps(resultList, cls=JSONEncoder)
  return renderWithCommonData(request, 'frontend/seasons.html', {
    "seasons": seasonList,
    "seasonsJSON": seasonsJSON
  })



def getDriversStandings(id: int):
  races = Race.objects.filter(season_id = id).order_by('startDate') # DriverRaceResult.objects.filter(driverEntry_id=driverEntry.id)
  viewList = {}
  raceCount = races.count()
  for raceIndex, race in enumerate(races):
    results = getRaceResult(race.id)
    for driver in results:
      driverId = driver["id"]
      if driverId not in viewList: # first race, create name column..
        viewList[driverId] = OrderedDict()
        for columnName, columnValue in COLUMNS["drivers"].items():
          viewList[driverId][columnName] = driver[columnValue]
        viewList[driverId]["sum"] = 0   
        viewList[driverId]["points"] = [0]*raceCount
        viewList[driverId]["finishstates"] = ["-"]*raceCount
      
      viewList[driverId]["points"][raceIndex] = int(driver["sumPointsRace"]) # contains bonus points also
      viewList[driverId]["finishstates"][raceIndex]  = driver["finishstatus"]
      viewList[driverId]["sum"] = reduce(lambda x,y: x+y, viewList[driverId]["points"])
  viewList = list(viewList.values())
  return sorted(viewList, key=lambda tup: tup["sum"], reverse=True)

def get_incidents(request, id: int):
  race = Race.objects.all().filter(pk=id).get()
  incidents = Incident.objects.filter(race__season_id=race.season.id, race=race).exclude(result='')
  incidentsPendingCount = Incident.objects.filter(race__season_id=race.season.id, race=race, result='').count()
  return renderWithCommonData(request, 'frontend/incidents.html', {
    "race": race,
    "incidents": incidents,
    "incidentsPendingCount": incidentsPendingCount
  })
@cache_page(60 * 15)
def get_raceDetail(request, id: int):
  race = Race.objects.all().filter(pk=id).get()
  resultList = getRaceResult(race.id)
  if  RaceResult.objects.all().filter(race_id=id).count() == 0:
    return renderWithCommonData(request, 'frontend/race.html', {
      "race": race,
      "resultList": None,
      "title":  race.name,
      "streamLink": race.streamLink,
      "commentatorInfo": race.commentatorInfo
    })
  incidentsCount = Incident.objects.filter(race__season_id=race.season.id, race=race).count()
  return renderWithCommonData(request, 'frontend/race.html', {
    "race": race,
    "resultList": resultList,
    "title":  race.name,
    "streamLink": race.streamLink,
    "commentatorInfo": race.commentatorInfo,
    "incidentsCount": incidentsCount
  })
def isSeasonFinished(season):
  races = Race.objects.filter(season=season).order_by('startDate') 
  return not season.isRunning or season.round == races.count()
@cache_page(60 * 15)
def get_seasonStandingsTeams(request, id: int):
  racesRaw = Race.objects.filter(season_id=id).order_by('startDate') 
  resultList = getTeamStandings(id)
  season = Season.objects.all().filter(pk=id).get()
  titleAttachment = ""
  if isSeasonFinished(season):
    titleAttachment = " - Final results"

  return renderWithCommonData(request, 'frontend/standings.html', {
    "resultList":  enumerate(resultList),
    "isDriverStandings": False,
    "races": racesRaw,
    "title": "Team standing - " + season.name + titleAttachment,
    "season": season,
    "textBlocks": TextBlock.objects.filter(season_id=id, context="tstandings"),
    "containerWidth": getRaceContainerWidth(racesRaw.count())
  })
  
def getRaceContainerWidth(raceCount: int) -> float:
  return 100/raceCount

@cache_page(60 * 15)
def get_seasonStandingsDrivers(request, id: int):
  resultList = getDriversStandings(id)
  racesRaw = Race.objects.filter(season_id=id).order_by('startDate') 
  season = Season.objects.all().filter(pk=id).get()
  titleAttachment = ""
  if isSeasonFinished(season):
    titleAttachment = " - Final results"
  return renderWithCommonData(request, 'frontend/standings.html', {
    "resultList": enumerate(resultList),
    "isDriverStandings": True,
    "races": racesRaw,
    "title": "Drivers standing - " + season.name + titleAttachment,
    "season": season,
    "textBlocks": TextBlock.objects.filter(season_id=id, context="dstandings"),
    "containerWidth": getRaceContainerWidth(racesRaw.count())
  })

def signUp(request):
  if LEAGUECONFIG["staticSignup"]:
    textBlocks = TextBlock.objects.filter(context='signup')
    return renderWithCommonData(request, 'frontend/signup.html', { "textBlocks": textBlocks})
  form = RegistrationForm()
  token = None

  if request.POST:
    form = RegistrationForm(request.POST,request.FILES)
    if form.is_valid():
      registrationData = form.save(commit=False)
      registrationData.save()
      token = registrationData.token
      form = None
      token = registrationData.token
  return renderWithCommonData(request, 'frontend/signup.html', {
    "form": form,
    "token": token
  })

def liverySubmission(request):
  form = LiverySubmissionForm()
  submitted = False
  if request.POST:
    form = LiverySubmissionForm(request.POST,request.FILES)
    if form.is_valid():
      livery = form.save(commit=False)
      livery.save()
      submitted = True
  return renderWithCommonData(request, 'frontend/livery.html', {
    "form": form,
    "submitted": submitted
  })

def privacyAccept(request):
  if not LEAGUECONFIG["staticSignup"]:
    raise Http404("Page does not exist")
  form = GenericPrivacyAcceptAcceptForm()
  submitted = False

  if request.POST:
    form = GenericPrivacyAcceptAcceptForm(request.POST,request.FILES)
    if form.is_valid():
      acceptData = form.save(commit=False)
      acceptData.userAgent = request.META['HTTP_USER_AGENT']
      acceptData.ipAddress = getClientIP(request)
      acceptData.save()
      submitted = True
     
  return renderWithCommonData(request, 'frontend/privacyaccept.html', {
    "form": form,
    "submitted": submitted
  })

def driverOfTheDayVote(request, id: int):
  if not LEAGUECONFIG["dotd"]:
    raise Http404()
  season = Season.objects.get(id=id)
  if not season.driverOfTheDayVote:
    raise Http404()
  form = DriverOfTheDayVoteForm()
  form.season = season
  submitted = False
  error = None
  if DriverOfTheDayVote.objects.filter(season=season,ipAddress=getClientIP(request)).count():
    # visitor already voted for something
    error = "You already voted"
  if request.POST:
    form = DriverOfTheDayVoteForm(request.POST)
    if form.is_valid():
      vote = form.save(commit=False)
      vote.season = season
      if DriverOfTheDayVote.objects.filter(season=season,ipAddress=getClientIP(request)).count() == 0:
        vote.ipAddress = getClientIP(request)
        vote.save()
        submitted = True
      else:
        error = "You already voted"
      
     
  return renderWithCommonData(request, 'frontend/driveroftheday.html', {
    "season": season,
    "form": form,
    "submitted": submitted,
    "error": error
  })

def incidentReport(request):
  form = IncidentForm()
  if request.POST:
    form = IncidentForm(request.POST,request.FILES)
    if form.is_valid():
      data = form.save(commit=False)
      data.save()
      form = None
  return renderWithCommonData(request, 'frontend/incident.html', {
    "form": form
  })
@cache_page(60 * 15)
def get_iCalender(request, id: int):
  tz = pytz.timezone(LEAGUECONFIG["timezone"])
  calendar = Calendar()
  calendar.add('prodid', '-//SimPaddock//')
  calendar.add('version', '2.0')
  season = Season.objects.filter(pk=id).first()
  if season is None:
    raise Http404()
  races = Race.objects.filter(season_id=season.id)
  for race in races:
    event = Event()
    event.add("DTSTART", race.startDate.replace(tzinfo=tz))
    event.add("DTEND", race.endDate.replace(tzinfo=tz))
    event.add("SUMMARY", race.name)
    event.add("LOCATION", LEAGUECONFIG["name"])
    calendar.add_component(event)
  response =HttpResponse(calendar.to_ical(), content_type="text/calendar")
  response['Content-Disposition'] = 'attachment; filename="{0}.ics"'.format(season.name)
  return response


def getDriverStats(request, id: int):
  from statistics import mean
  from math import floor
  driver = Driver.objects.filter(id=id).get()
  races = DriverRaceResult.objects.filter(driverEntry__driver_id=id).count()
  seasonsAttended = DriverEntry.objects.filter(driver_id=id).values_list('teamEntry__season',named=True)
  
  positions = list(map(int, DriverRaceResultInfo.objects.filter(driverRaceResult__driverEntry__driver_id=id,name='position').values_list('value', flat=True)))
  points = list(map(int, DriverRaceResultInfo.objects.filter(driverRaceResult__driverEntry__driver_id=id,name='points').values_list('value', flat=True)))
  nonOkayRacesRaw =  DriverRaceResultInfo.objects.filter(driverRaceResult__driverEntry__driver_id=id,name='finishstatus').values_list('value', flat=True)
  raceResults =[]
  for nonOkayRaceRaw  in nonOkayRacesRaw:
    if "Normally" in nonOkayRaceRaw:
      raceResults.append(0)
    else:
      raceResults.append(1)
      
  driverEntries = DriverEntry.objects.filter(driver_id=id)
  seasons = Season.objects.filter(pk__in=seasonsAttended)
  title = "{0}, {1}".format(driver.lastName, driver.firstName)
  return renderWithCommonData(request, 'frontend/profile.html', {
    "title": title,
    "avgPosition": floor(mean(positions)),
    "worsePosition": max(positions),
    "bestPosition": min(positions),
    "driverEntries": driverEntries,
    "seasons": seasons,
    "pointsSparkline": generateSparkline(points),
    "positionSparkline": generateSparkline(positions),
    "dnfSparkline": generateSparkline(raceResults),
    "dnfCount": raceResults.count(1),
    "racesCount": races,
    "driver": driver
  })

def maintenance(request):
  return renderWithCommonData(request, 'frontend/maintenance.html', {})

def plate(request):
  form = NumberPlateForm()
  if request.method=='POST':
      form = NumberPlateForm(request.POST)
      if form.is_valid():
          formData = form.cleaned_data
          #now in the object cd, you have the form as a dictionary.
          number = int(formData.get('number'))
          if number > 100 or number == 0:
            return HttpResponse("Number invalid")
          from PIL import Image
          file = Upload.objects.filter(name = "plate").get()
          img = Image.open(file.filePath.path)
          draw = ImageDraw.Draw(img)
          font =ImageFont.truetype( size=400, font=STATIC_ROOT + "/frontend/fonts/electrolize-v6-latin-regular.ttf")
          text = str(number)
          offsets = NUMBERGENERATOROFFSETS
          if len(text) == 2:
            draw.text((70+ offsets[int(text[0])], 80),text[0],(50,55,55),font=font)
            draw.text((330+ offsets[int(text[1])], 80),text[1],(50,55,55),font=font)
          else:
            draw.text((200 + offsets[number], 80),str(number),(50,55,55),font=font)
          response = HttpResponse(content_type="image/jpeg")
          img.save(response, "JPEG")
          return response
  return renderWithCommonData(request, 'frontend/numberplate.html', { "form": form})


def embedYoutube(request,argument: str):
  url = "{0}video/youtube/{1}".format(LEAGUECONFIG["embettyUrl"],argument)
  r = get(url)
  contentType = r.headers['content-type']
  return HttpResponse(r.content, content_type=contentType)