from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from collections import OrderedDict
from django.db import models
from django.http import Http404
from .models import Upload, RegistrationStatus, TextBlock, NewsArticle, Season, Race, TeamEntry, Track, RaceResult, DriverRaceResult, DriverRaceResultInfo, DriverEntry, Driver, Team
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
from pitlane.settings import STATIC_ROOT, LEAGUECONFIG, MEDIA_ROOT
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from icalendar import Calendar, Event
import pytz
from datetime import datetime, date, time
from urllib.parse import urljoin
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
import base64
LIST_DATA_RACE = "race"
LIST_DATA_TEAM_STANDINGS = "teams"
LIST_DATA_DRIVERS_STANDINGS = "drivers"
LIST_DATA_DRIVERS ="listdrivers"

COLUMNS = {
  "race": OrderedDict([
    ('position', None), 
    ('id', "baseInfos.driverEntry.driver.id"), 
    ('country', "baseInfos.driverEntry.driver.country"), 
    ('firstName', "baseInfos.driverEntry.driver.firstName"),
    ('lastName', "baseInfos.driverEntry.driver.lastName"),
    ('team', "baseInfos.driverEntry.teamEntry.team.name"),
    ('teamid', "baseInfos.driverEntry.teamEntry.team.id"),
    ('logo', "baseInfos.driverEntry.teamEntry.team.logo"),
    ('vehicle', "baseInfos.driverEntry.teamEntry.vehicle"),
    ('vehicleImage', "baseInfos.driverEntry.teamEntry.vehicleImage"),
    ('number', "baseInfos.driverEntry.driverNumber"),
    ('numberFormat', "baseInfos.driverEntry.driverNumberFormat"),
    ('laps', None), # none leads to direct additional searching
    ('stops', None),
    ('time', None),
    ('avg', None),
    ('points', None),
    ('finishstatus', None),
    ('controlandaids', None),
    ('bonuspoints', None),
    ('cartype', None), # actual car class from rFactor reported
  ]),
  "drivers": OrderedDict([
    ('id', "id"), 
    ('firstName', "firstName"),
    ('lastName', "lastName"),
    ('team', "team"),
    ('logo', "logo"),
    ('vehicle', "vehicle"),
    ('number', "number"),
    ('country', "country")
  ]),
  "teams": OrderedDict([
    ('team', "team"),
    ('logo', "logo"),
    ('vehicle', "vehicle"),
    ('vehicleImage', "vehicleImage")
  ])
}

from pitlane.settings import LEAGUECONFIG

def getRoutes():
  routes = OrderedDict()
  season = getCurrentCup()
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

def getCurrentCup():
  nextRace = Race.objects.filter(season__isRunning=True, endDate__gt=datetime.now()).order_by("startDate").first()
  if nextRace is None:
    return None
  
  cup = nextRace.season
  cup.nextRace = nextRace
  return cup

def renderWithCommonData(request, template, context):
  context["routes"] = getRoutes()
  context["config"] = LEAGUECONFIG
  context["running"] = getCurrentCup()
  template = template.replace("frontend/", "frontend/" + LEAGUECONFIG["theme"] + "/")
  context["baseLayout"] = 'frontend/'+  LEAGUECONFIG["theme"] + '/layout.html'
  return render(request, template, context)

def get_index(request):
  tz = pytz.timezone(LEAGUECONFIG["timezone"])
  gmt = datetime.now(tz)
  now = str(gmt.replace(microsecond=0))
  races = Race.objects.all().filter(season=getCurrentCup()).order_by("startDate")
  newsArticles = NewsArticle.objects.filter(isDraft=False).order_by("-date")[:12]
  textBlocks = TextBlock.objects.filter(context='landing')
  return renderWithCommonData(request, 'frontend/index.html', {
    "events": races,
    "newsArticles": newsArticles,
    "textBlocks": textBlocks,
    "now": now
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
  shareButtons = [
    {
      "name": "Twitter",
      "icon": "fab fa-twitter-square",
      "url": "https://twitter.com/intent/tweet?url=" + url + '&text=' + title
    },
    {
      "name": "Facebook",
      "icon": "fab fa-facebook-square",
      "url": "http://www.facebook.com/sharer.php?u=" + url
    },
    {
      "name": "reddit",
      "icon": "fab fa-reddit-square",
      "url": "https://reddit.com/submit?url=" + url + '&title=' + title
    },
    {
      "name": "reddit",
      "icon": "fab fa-get-pocket",
      "url": "https://getpocket.com/edit?url=" +url
    },
    {
      "name": "reddit",
      "icon": "fab fa-flipboard",
      "url": "https://share.flipboard.com/bookmarklet/popout?v=2&title=" + title + '&url=' + url
    },
    {
      "name": "pinterest",
      "icon": "fab fa-pinterest",
      "url": "http://pinterest.com/pin/create/button/?url=" + url
    },
    {
      "name": "RSS",
      "icon": "fas fa-rss",
      "url": "/feed"
    }
  ]
  return renderWithCommonData(request, 'frontend/article.html', {
    "articles": paginator.get_page(page),
    "shareButtons": shareButtons,
    "title": title
  })

def getSeasonDrivers(seasonId: int) -> list:
  teams = TeamEntry.objects.all().filter(season_id=seasonId)
  drivers = list()
  for team in teams:
    teamDrivers = DriverEntry.objects.all().filter(teamEntry_id=team.id)
    for driver in teamDrivers:
      drivers.append(driver) # FIXME: full object leads to json error
  return drivers

class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        return str(o)

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


def getChildValue(haystack, needle):
  parts = needle.split(".")
  value = haystack
  for part in parts:
    # last parent is dict or object -> extract children
    if isinstance(value, dict):
      value = value[part]
    elif isinstance(value, models.Model):
      value = getattr(value, part)
    elif isinstance(value, object):
      value = value.__dict__[part]
  return value

def getRaceResult(id: int):
  results = DriverRaceResult.objects.all().filter(raceResult__race_id=id)
  completeResults = []
  # collect all infos
  seasonId=None
  knownDrivers = []
  for result in results:
    seasonId = result.driverEntry.teamEntry.season.id
    infos = DriverRaceResultInfo.objects.all().filter(driverRaceResult_id=result.id)
    knownDrivers.append(result.driverEntry.driverNumber)
    completeResults.append(
      {
        "baseInfos": result,
        "additionalInfos": infos,
        "position": 0
      })
  # get all drivers to append DNS entries
  drivers = DriverEntry.objects.filter(teamEntry__season__id=seasonId)
  for driver in drivers:
    infos = {
      "laps": "0",
      "points": "0",
      "stops": "0",
      "position": "999",
      "finishstatus": "DNS",
      "cartype": ""
    }
    if driver.driverNumber not in knownDrivers:
      infosToAppend = []
      for key, info in infos.items():
        raceresultinfo = DriverRaceResultInfo()
        raceresultinfo.name = key
        raceresultinfo.value=info
        infosToAppend.append(raceresultinfo)
      completeResults.append(
      {
        "position":999,
        "baseInfos": {
          "driverEntry": driver
        },
        "additionalInfos": infosToAppend
      })

  viewList = []
  for result in completeResults:
    viewData = OrderedDict()
    viewData["position"] = 999
    viewData["points"] = 0
    viewData["finishstatus"]  = ""
    viewData["cartype"]  = ""
    viewData["bonuspoints"] = 0
    for columnName, columnPath in COLUMNS["race"].items():
      if columnPath is None:  # None means "search in additional fields"
        for info in result["additionalInfos"]:
          if info.name.lower() == columnName:
            valueToAdd = info.value
            if columnName in ["bonuspoints"]: # only sum bonus points together
              viewData[columnName] = viewData[columnName] + int(valueToAdd)
            else:
              viewData[columnName] = valueToAdd
      else:
        viewData[columnName] = getChildValue(result, columnPath)
    viewData["number"] =  viewData["numberFormat"].format(viewData["number"])
    # Alter the results if a driver was disqualified (after) the race booking
    if "finishstatus" in viewData and viewData["finishstatus"] == "dsq":
      viewData["position"] = 999
      viewData["points"] = 0
    if viewData["cartype"]:
      viewData["vehicle"] = viewData["cartype"] # the actual cartype overwrites the team entry vehicle
    viewData["sumPointsRace"] = int(viewData["points"]) + int(viewData["bonuspoints"]) # add bonus points
    viewList.append(viewData)
  return sorted(viewList, key=lambda x: int(x["position"]), reverse=False)

def getTeamStandings(id: int):
  races = Race.objects.filter(season_id = id).order_by('startDate')
  viewList = {}
  for key, race in enumerate(races):
    results = getRaceResult(race.id)
    for driver in results:
      teamId = driver["teamid"]
      if teamId not in viewList: # first race, create name column..
        viewList[teamId] = OrderedDict()
        for columnName, columnValue in COLUMNS["teams"].items():
          viewList[teamId][columnName] = driver[columnValue]
        viewList[teamId]["sum"] = 0   
        viewList[teamId]["points"] = []
        viewList[teamId]["detailPoints"] = []
      if len( viewList[teamId]["points"]) > key:
        # we already seen a result for that race
        viewList[teamId]["points"][key].append(int(driver["sumPointsRace"])) # sum bonus points also
        viewList[teamId]["detailPoints"][key].append(int(driver["sumPointsRace"])) # sum bonus points also
      else:
        viewList[teamId]["points"].append([int(driver["sumPointsRace"])]) # sum bonus points also
        viewList[teamId]["detailPoints"].append([int(driver["sumPointsRace"])]) # sum bonus points also
  viewList = list(viewList.values())
  # Rule: only the first two drivers will score
  for teamIndex, team in enumerate(viewList):
    teamPointSum = 0
    for key, race in enumerate(team["points"]):
      newRacePoints = sorted(race, reverse=True)
      if len(newRacePoints) > 2:
        newRacePoints = newRacePoints[0:2]
      newRacePointsSum = reduce(lambda x,y: int(x)+int(y),  newRacePoints)
      teamPointSum = teamPointSum + newRacePointsSum
      viewList[teamIndex]["points"][key]  = newRacePointsSum
    
    viewList[teamIndex]["sum"] =teamPointSum
  return sorted(viewList, key=lambda tup: tup["sum"], reverse=True)


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
def getClientIP(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

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

def signUpStatus(request):
  form = SignUpStatusForm()
  data = None
  token = None
  steps = OrderedDict()
  stepsTexts = [
    "1. SignUp",
    "2. We review",
    "3. Livery get's uploaded",
    "4. You are ready to race"
  ]
  if request.POST:
    form = SignUpStatusForm(request.POST)
    if form.is_valid():
      token = form.cleaned_data['token']
      data = RegistrationStatus.objects.filter(registration__token=token).order_by("date")
      if data.count() > 0:
        steps[stepsTexts[0]] = True 
      else:
        steps[stepsTexts[0]] = False 
      for i in range(1,4):
        steps[stepsTexts[i]] = None

      if data.count() > 1: # there is more than one registration status
        steps[stepsTexts[1]] = True
        if data.filter(registration__wasUploaded=True, registration__ignoreReason="").count() > 1: # the 
          for i in range(1,4):
            steps[stepsTexts[i]] = True 
        if data.exclude(registration__ignoreReason="").count() > 1: # the submission was ignored
          steps[stepsTexts[1]] = True
          steps[stepsTexts[2]] = False
          steps[stepsTexts[3]] = False  

        
      
  return renderWithCommonData(request, 'frontend/signupstatus.html', {
    "form": form,
    "data": data,
    "token": token,
    "steps": steps
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

def embedYoutube(request,argument: str):
  url = "{0}video/youtube/{1}".format(LEAGUECONFIG["embettyUrl"],argument)
  r = get(url)
  contentType = r.headers['content-type']
  return HttpResponse(r.content, content_type=contentType)

def sparkline(data, figsize=(4, 0.25), **kwags):
  data = list(data)
  # based on https://markhneedham.com/blog/2017/09/23/python-3-create-sparklines-using-matplotlib/

  fig, ax = plt.subplots(1, 1, figsize=figsize, **kwags)
  ax.plot(data)
  for k,v in ax.spines.items():
      v.set_visible(False)
  ax.set_xticks([])
  ax.set_yticks([])

  plt.plot(len(data) - 1, data[len(data) - 1], 'r.')

  ax.fill_between(range(len(data)), data, len(data)*[min(data)], alpha=0.1)

  img = BytesIO()
  plt.savefig(img, transparent=True, bbox_inches='tight')
  img.seek(0)
  plt.close()

  return base64.b64encode(img.read()).decode("UTF-8")

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
    "pointsSparkline": sparkline(points),
    "positionSparkline": sparkline(positions),
    "dnfSparkline": sparkline(raceResults),
    "dnfCount": raceResults.count(1),
    "racesCount": races,
    "driver": driver,
    "sparklines": [
      sparkline(positions),
      sparkline(points),
      sparkline(raceResults)
    ]
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
          offsets = {
            1: -20,
            2: -30,
            3: -30,
            4: -40,
            5: -30,
            6: -30,
            7: -20,
            8: -40,
            9: -40
          }
          if len(text) == 2:
            draw.text((70+ offsets[int(text[0])], 80),text[0],(50,55,55),font=font)
            draw.text((330+ offsets[int(text[1])], 80),text[1],(50,55,55),font=font)
          else:
            draw.text((200 + offsets[number], 80),str(number),(50,55,55),font=font)
          response = HttpResponse(content_type="image/jpeg")
          img.save(response, "JPEG")
          return response
  return renderWithCommonData(request, 'frontend/numberplate.html', { "form": form})