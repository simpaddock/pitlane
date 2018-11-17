from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from collections import OrderedDict
from django.db import models
from django.http import Http404
from .models import RegistrationStatus, TextBlock, NewsArticle, Season, Race, TeamEntry, Track, RaceResult, DriverRaceResult, DriverRaceResultInfo, DriverEntry, Driver, Team, RaceOverlayControlSet
from django.core.serializers.json import DjangoJSONEncoder
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
  ]),
  "drivers": OrderedDict([
    ('id', "id"), 
    ('firstName', "firstName"),
    ('lastName', "lastName"),
    ('team', "team"),
    ('logo', "logo"),
    ('vehicle', "vehicle"),
    ('number', "number")
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
  text = "User-agent: *\nDisallow: /imprint/\nDisallow: /privacy/"
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
  newsArticles = NewsArticle.objects.all().order_by("-date")[:10]
  textBlocks = TextBlock.objects.filter(context='landing')
  return renderWithCommonData(request, 'frontend/index.html', {
    "events": races,
    "newsArticles": newsArticles,
    "textBlocks": textBlocks,
    "now": now
  })

#@cache_page(60 * 15)
def get_news(request):
  articles = NewsArticle.objects.all().order_by("-date")
  paginator = Paginator(articles, 50)
  page = request.GET.get('page')
  return renderWithCommonData(request, 'frontend/news.html', {
    "articles": paginator.get_page(page)
  })

#@cache_page(60 * 15)
def get_about(request):
  name = LEAGUECONFIG["name"]
  logo = LEAGUECONFIG["logo"]
  textBlocks = TextBlock.objects.filter(context='about')
  return renderWithCommonData(request, 'frontend/about.html', {
    "name": name,
    "logo": logo,
    "textBlocks": textBlocks
  })

#@cache_page(60 * 15)  
def get_rules(request):
  return renderWithCommonData(request, 'frontend/rules.html', {
    "rules": TextBlock.objects.filter(season__isRunning=True, context='rule')
  })

#@cache_page(60 * 15)
def get_privacy(request):
  return renderWithCommonData(request, 'frontend/privacy.html', {})

#@cache_page(60 * 15)
def get_imprint(request):
  return renderWithCommonData(request, 'frontend/imprint.html', {})

#@cache_page(60 * 15)
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

#@cache_page(60 * 15)
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
    for race in Race.objects.all().filter(season_id=seasonId):
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
      "finishstatus": "DNS"
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
    for columnName, columnPath in COLUMNS["race"].items():
      if columnPath is None:  # None means "search in additional fields"
        for info in result["additionalInfos"]:
          if info.name.lower() == columnName:
            viewData[columnName] = info.value
      else:
        viewData[columnName] = getChildValue(result, columnPath)
    viewData["number"] =  viewData["numberFormat"].format(viewData["number"])
    # Alter the results if a driver was disqualified (after) the race booking
    if "finishstatus" in viewData and viewData["finishstatus"] == "dsq":
      viewData["position"] = 999
      viewData["points"] = 0
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
        viewList[teamId]["points"][key].append(int(driver["points"]))
        viewList[teamId]["detailPoints"][key].append(int(driver["points"]))
      else:
        viewList[teamId]["points"].append([int(driver["points"])])
        viewList[teamId]["detailPoints"].append([int(driver["points"])])
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
      
      viewList[driverId]["points"][raceIndex] = int(driver["points"])
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
#@cache_page(60 * 15)
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
  raceResult = RaceResult.objects.all().filter(race_id=id).get()
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
#@cache_page(60 * 15)
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
    "textBlocks": TextBlock.objects.filter(season_id=id, context="tstandings")
  })

#@cache_page(60 * 15)
def get_raceBanner(request, id: int):
  race = Race.objects.filter(pk=id).get()
  schedule = TextBlock.objects.filter(title="Race Schedule", season_id=race.season.pk).first()
  if schedule is None: # we need a schedule...
    raise Http404()
  data = {
    "raceName": race.name,
    "startDate": "Start " + race.startDate.strftime(LEAGUECONFIG["dateFormat"]),
    "endDate": "End " + race.startDate.strftime(LEAGUECONFIG["dateFormat"]),
    "schedule": schedule.plainText,
    "url": LEAGUECONFIG["url"],
  }
  blocks = LEAGUECONFIG["bannerConfig"]
  img = Image.new('RGBA', (1920, 1080), (0,0,0,0))
  race = Race.objects.filter(pk=id).get()
  draw = ImageDraw.Draw(img)
  for block in blocks:
    if block["type"].lower() == "image":
      blockImage = Image.open(MEDIA_ROOT + block["path"], 'r')
      wasResized = False
      if block["filter"] is not None:
        blockImage = blockImage.convert(block["filter"])
      if block["size"] is not None:
        blockImage = blockImage.resize(tuple(block["size"]))
        wasResized = True
      if wasResized:
        img.paste(blockImage, tuple(block["position"]), blockImage) # only use the transparency map if the size was altered
      else:
        img.paste(blockImage, tuple(block["position"]))
    if block["type"].lower() == "text":
      text = data[block["text"]]
      draw.text(tuple(block["position"]), text, font=ImageFont.truetype( size=int(block["fontSize"]), font=STATIC_ROOT + block["fontPath"]), fill=tuple(block["fontColor"]))
    if block["type"].lower() == "multilinetext":
      text = data[block["text"]]
      draw.multiline_text(tuple(block["position"]), text, font=ImageFont.truetype( size=int(block["fontSize"]), font=STATIC_ROOT + block["fontPath"]), fill=tuple(block["fontColor"]))
    

      
  response = HttpResponse(content_type="image/png")
  img.save(response, "PNG")
  return response

#@cache_page(60 * 15)
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
    "textBlocks": TextBlock.objects.filter(season_id=id, context="dstandings")
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
#@cache_page(60 * 15)
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
  positions = list(map(int, DriverRaceResultInfo.objects.filter(driverRaceResult__driverEntry__driver_id=id,name='position').values_list('value', flat=True)))
  points = list(map(int, DriverRaceResultInfo.objects.filter(driverRaceResult__driverEntry__driver_id=id,name='points').values_list('value', flat=True)))
  nonOkayRacesRaw =  DriverRaceResultInfo.objects.filter(driverRaceResult__driverEntry__driver_id=id,name='finishstatus').values_list('value', flat=True)
  raceResults =[]
  for nonOkayRaceRaw  in nonOkayRacesRaw:
    if "Normally" in nonOkayRaceRaw:
      raceResults.append(0)
    else:
      raceResults.append(1)
      
  teamEntries = DriverEntry.objects.filter(driver_id=id).values_list('teamEntry__team',named=True)
  teams = Team.objects.filter(pk__in=teamEntries)
  title = "{0}, {1}".format(driver.lastName, driver.firstName)
  return renderWithCommonData(request, 'frontend/profile.html', {
    "title": title,
    "avgPosition": floor(mean(positions)),
    "worsePosition": max(positions),
    "bestPosition": min(positions),
    "teams": teams,
    "pointsSparkline": sparkline(points),
    "positionSparkline": sparkline(positions),
    "dnfSparkline": sparkline(raceResults),
    "dnfCount": raceResults.count(1),
    "sparklines": [
      sparkline(positions),
      sparkline(points),
      sparkline(raceResults)
    ]
  })