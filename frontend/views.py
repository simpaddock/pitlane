from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from collections import OrderedDict
from django.db import models

from .models import NewsArticle, Season, Race, TeamEntry, Track, RaceResult, DriverRaceResult, DriverRaceResultInfo, DriverEntry, Driver, Team, RaceOverlayControlSet
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from json import dumps, loads
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import filetype
from functools import reduce
from .forms import *
from requests import get
from django.views.decorators.csrf import csrf_exempt

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
    routes[LEAGUECONFIG["pitlane"]] = "Pitlane"
  return routes

def get_robots(request):
  return HttpResponse("foo", content_type='text/plain')

def getCurrentCup():
  cup =  Season.objects.filter(isRunning=True).first()
  if cup is not None:
    # next race
    nextRace = Race.objects.filter(season_id=cup.id).order_by("-startDate").first()
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
  articles = NewsArticle.objects.all().order_by("date")
  newsflashArticle = None
  mediaFile = None
  isVideo = False
  if len(articles) > 0:
    newsflashArticle = articles[0]
    if newsflashArticle.mediaFile:
      mediaFile = 'frontend/' + newsflashArticle.mediaFile.url
      isVideo =  "video" in filetype.guess(newsflashArticle.mediaFile.path).mime
  return renderWithCommonData(request, 'frontend/index.html', {
    "newsflashArticle": newsflashArticle,
    "mediaFile":  mediaFile,
    "isVideo": isVideo
  })

def get_news(request):
  articles = NewsArticle.objects.all().order_by("date")
  paginator = Paginator(articles, 5)
  page = request.GET.get('page')
  return renderWithCommonData(request, 'frontend/news.html', {
    "articles": paginator.get_page(page)
  })
def get_about(request):
  name = LEAGUECONFIG["name"]
  logo = LEAGUECONFIG["logo"]
  established = LEAGUECONFIG["established"]
  raceCount = Race.objects.all().count()
  teamCount = Team.objects.all().count()
  driverCount = Driver.objects.all().count()
  seasonCount = Season.objects.all().count()
  return renderWithCommonData(request, 'frontend/about.html', {
    "established": established,
    "name": name,
    "logo": logo,
    "raceCount": raceCount,
    "teamCount": teamCount,
    "driverCount": driverCount,
    "seasonCount": seasonCount
  })

def get_SingleNews(request, id:int):
  articles = NewsArticle.objects.all().filter(pk=id)
  paginator = Paginator(articles, 5)
  page = request.GET.get('page')
  return renderWithCommonData(request, 'frontend/news.html', {
    "articles": paginator.get_page(page)
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

def get_seasonList(request):
  seasonList = Season.objects.all()
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
    knownDrivers.append(result.driverEntry.driver.id)
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
    if driver.id not in knownDrivers:
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
    for columnName, columnPath in COLUMNS["race"].items():
      if columnPath is None:  # None means "search in additional fields"
        for info in result["additionalInfos"]:
          if info.name.lower() == columnName:
            viewData[columnName] = info.value
        if columnName not in viewData:
          viewData[columnName] = "-"
      else:
        viewData[columnName] = getChildValue(result, columnPath)
    viewData["number"] =  viewData["numberFormat"].format(viewData["number"])
    viewList.append(viewData)
  return sorted(viewList, key=lambda x: int(x["position"]), reverse=False)

def getTeamStandings(id: int):
  races = Race.objects.filter(season_id = id) # DriverRaceResult.objects.filter(driverEntry_id=driverEntry.id)
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

      if len( viewList[teamId]["points"]) > key:
        # we already seen a result for that race
        viewList[teamId]["points"][key] = viewList[teamId]["points"][key] + int(driver["points"])
      else:
        viewList[teamId]["points"].append(int(driver["points"]))
      viewList[teamId]["sum"] = reduce(lambda x,y: x+y, viewList[teamId]["points"])
      
  viewList = list(viewList.values())
  return sorted(viewList, key=lambda tup: tup["sum"], reverse=True)

def getDriversStandings(id: int):
  races = Race.objects.filter(season_id = id).order_by('startDate') # DriverRaceResult.objects.filter(driverEntry_id=driverEntry.id)
  viewList = {}
  for race in races:
    results = getRaceResult(race.id)
    for driver in results:
      driverId = driver["id"]
      if driverId not in viewList: # first race, create name column..
        viewList[driverId] = OrderedDict()
        for columnName, columnValue in COLUMNS["drivers"].items():
          viewList[driverId][columnName] = driver[columnValue]
        viewList[driverId]["sum"] = 0   
        viewList[driverId]["points"] = []
      
      viewList[driverId]["points"].append(int(driver["points"]))
      viewList[driverId]["sum"] = reduce(lambda x,y: x+y, viewList[driverId]["points"])
  viewList = list(viewList.values())
  return sorted(viewList, key=lambda tup: tup["sum"], reverse=True)

def get_raceDetail(request, id: int):
  race = Race.objects.all().filter(pk=id).get()
  resultList = getRaceResult(race.id)
  raceResult = RaceResult.objects.all().filter(race_id=id).get()
  return renderWithCommonData(request, 'frontend/race.html', {
    "race": race,
    "resultList": resultList,
    "title":  race.name,
    "streamLink": raceResult.streamLink,
    "commentatorInfo": raceResult.commentatorInfo 
  })

def get_seasonStandingsTeams(request, id: int):
  racesRaw = Race.objects.filter(season_id=id).order_by('startDate') 
  resultList = getTeamStandings(id)
  return renderWithCommonData(request, 'frontend/standings.html', {
    "resultList":  enumerate(resultList),
    "isDriverStandings": False,
    "races": racesRaw,
    "title": "Team standing - " + Season.objects.all().filter(pk=id).get().name
  })

def get_seasonStandingsDrivers(request, id: int):
  resultList = getDriversStandings(id)
  racesRaw = Race.objects.filter(season_id=id).order_by('startDate') 
  return renderWithCommonData(request, 'frontend/standings.html', {
    "resultList": enumerate(resultList),
    "isDriverStandings": True,
    "races": racesRaw,
    "title": "Drivers standing - " + Season.objects.all().filter(pk=id).get().name
  })

def signUp(request):
  form = TeamSignUpForm()
  if request.POST:
    form = TeamSignUpForm(request.POST,request.FILES)
  return renderWithCommonData(request, 'frontend/signup.html', {
    "form": form,
  })

def signUpTeam(request):
  form = TeamSignUpForm()
  if request.POST:
    form = TeamSignUpForm(request.POST,request.FILES)
  return renderWithCommonData(request, 'frontend/signup.html', {
    "form": form,
  })

def signUpDriver(request):
  form = DriverSignUpForm()
  if request.POST:
    form = DriverSignUpForm(request.POST,request.FILES)
  return renderWithCommonData(request, 'frontend/signup.html', {
    "form": form,
  })
# JSON API Endpoints


def get_raceData(request, id: int):
  race = Race.objects.get(pk=id)
  entries = DriverEntry.objects.filter(teamEntry__season_id=race.season.id)
  result = []
  for entry in entries:
    # get relevant infos only.
    resultData = {
      "driverNumber": entry.driverNumber,
      "driverNumberFormat": entry.driverNumberFormat,
      "teamName": entry.teamEntry.team.name,
    }
    result.append(resultData)
  cameraControl = RaceOverlayControlSet.objects.filter(race_id=id).first()
  if cameraControl is not None:
    return JsonResponse({
      "entries": result,
      "controlSet": cameraControl.controlSet,
      "slotId": cameraControl.slotId,
      "cameraId":  cameraControl.cameraId,
      "commandId": cameraControl.id
    }, safe=False)
  else:
    return JsonResponse({
      "entries": result,
      "controlSet": -1,
      "slotId": -1,
      "cameraId":  -1,
      "commandId": -1
    }, safe=False)

# Overlay control panel
@csrf_exempt 
def get_overlayControl(request, id: int):
  if request.method  == "POST":
    race = Race.objects.get(pk=id)
    lastControlSet = RaceOverlayControlSet.objects.first()
    
    RaceOverlayControlSet.objects.filter(race_id=id).delete()
    data = loads(request.body.decode("utf-8"))
    overlay = RaceOverlayControlSet()
    overlay.race = race
    driver = data["driver"]
    position = data["position"]
    overlay.cameraId = int(data["cameraId"])
    if driver is not None:
      overlay.slotId = driver
      overlay.controlSet = dumps({
        "driver": driver
      })
    if position is not None:
      overlay.slotId = position
      overlay.controlSet = dumps({
        "battle": position
      })
    if "pause" in data and data["pause"] == True:
      overlay.slotId = -1
      overlay.controlSet = dumps({
        "pause": True
      })
    overlay.save()
    return JsonResponse({})
  else:
    return HttpResponse("Nein")