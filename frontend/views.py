from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from collections import OrderedDict
from django.db import models

from .models import NewsArticle, Season, Race, TeamEntry, Track, RaceResult, DriverRaceResult, DriverRaceResultInfo, DriverEntry, Driver, Team, RaceOverlayControlSet
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from json import dumps
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import filetype
from functools import reduce


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
    ('logo', "baseInfos.driverEntry.teamEntry.team.logo"),
    ('vehicle', "baseInfos.driverEntry.teamEntry.vehicle"),
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
    ('number', "number"),
  ])
}

from pitlane.settings import LEAGUECONFIG

def getRoutes():
  routes = OrderedDict()
  routes["news"] = "News"
  routes["seasons"] = "Seasons"
  routes["drivers"] = "Drivers"
  routes["teams"] = "Teams"
  routes["contact"] = "contact"
  routes["pitlane"] = "Pitlane"
  return routes

def get_robots(request):
  return HttpResponse("foo", content_type='text/plain')

def renderWithCommonData(request, template, context):
  context["routes"] = getRoutes()
  context["config"] = LEAGUECONFIG
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
  paginator = Paginator(articles, 1)
  page = request.GET.get('page')
  return renderWithCommonData(request, 'frontend/news.html', {
    "articles": paginator.get_page(page)
  })

def get_SingleNews(request, id:int):
  articles = NewsArticle.objects.all().filter(pk=id)
  paginator = Paginator(articles, 1)
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
      drivers.append(driver.id) # FIXME: full object leads to json error
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
  results = DriverRaceResult.objects.all().filter(raceResult_id=id)
  completeResults = []
  # collect all infos
  for result in results:
    infos = DriverRaceResultInfo.objects.all().filter(driverRaceResult_id=result.id)
    completeResults.append(
      {
        "baseInfos": result,
        "additionalInfos": infos,
        "position": 0
      }
    )
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
  return sorted(viewList, key=lambda x: x["position"], reverse=False)

def getTeamStandings(id: int):
  results = TeamEntry.objects.all().filter(season_id=id)
  completeResults = []
  # collect all infos
  for result in results:
    infos = []
    driverEntries = DriverEntry.objects.all().filter(teamEntry_id=result.id)
    teamPoints = 0
    for driverEntry in driverEntries:
      # get race results
      races = DriverRaceResult.objects.filter(driverEntry_id=driverEntry.id)
      racePoints = 0
      for race in races:
        driverPoints = DriverRaceResultInfo.objects.filter(driverRaceResult_id=race.id).filter(name='Points')
        for point in driverPoints:
          racePoints = racePoints + int(point.value)
      # add per race sum
      pointColumn = DriverRaceResultInfo()
      pointColumn.name = race.raceResult.race.name
      pointColumn.value = racePoints
      infos.append(pointColumn)
      teamPoints = teamPoints + racePoints
    
    # add a sum column
    pointColumn = DriverRaceResultInfo()
    pointColumn.name = "Points"
    pointColumn.value = teamPoints
    infos.append(pointColumn)

    # append to complete list
    completeResults.append(
      {
        "baseInfos": result,
        "additionalInfos": infos,
        "position": 0
      }
    )
  # rank them
  for result in completeResults:
    result["position"] =  getRank(result, completeResults, "Points", True)
  
  # prepare additional columns types
  additionalColumnsNames = OrderedDict()
  
  additionalColumnsNames["Points"] = "int"
  races = Race.objects.filter(season_id=id)
  for race in races:
    additionalColumnsNames[race.name] = "int"
  



  # flatten te list for displaying
  viewList = []
  for result in completeResults:
    viewData = OrderedDict()
    viewData["position"] = result["position"], "position"
    viewData["name"] = result["baseInfos"].team.name, "longstr"
    for additionalColumnKey, additionalColumnType in additionalColumnsNames.items():
      for info in result["additionalInfos"]:
        print(info.value, info.name)
        if info.name == additionalColumnKey:
          viewData[info.name] = info.value, additionalColumnType
    viewList.append(viewData)
  print(viewList)
  return viewList

def getDriversStandings(id: int):
  races = Race.objects.filter(season_id = id) # DriverRaceResult.objects.filter(driverEntry_id=driverEntry.id)
  viewList = {}
  for key, race in enumerate(races):
    results = getRaceResult(race.id)
    for driver in results:
      driverId = driver["id"]
      if driverId not in viewList: # first race, create name column..
        viewList[driverId] = OrderedDict()
        for columnName, columnValue in COLUMNS["drivers"].items():
          viewList[driverId][columnName] = driver[columnValue]

      viewList[driverId][race.name] = driver["points"]
  print(viewList)
  return viewList

def getTeamList():
  drivers = Team.objects.all()
  completeResults = []
  
  for driver in drivers:
    infos = []
    completeResults.append(
      {
        "baseInfos": driver,
        "additionalInfos": infos,
        "position": 0
      }
    )
  # rank them
  for result in completeResults:
    result["position"] =  getRank(result, completeResults, "Points", True)
  
  # prepare additional columns types
  additionalColumnsNames = OrderedDict()

  # flatten te list for displaying
  viewList = []
  for result in completeResults:
    viewData = OrderedDict()
    viewData["name"] = result["baseInfos"].name, "longstr"
    viewData["logo"] = result["baseInfos"].logo, "longstr"
    for additionalColumnKey, additionalColumnType in additionalColumnsNames.items():
      for info in result["additionalInfos"]:
        if info.name == additionalColumnKey:
          viewData[info.name] = info.value, additionalColumnType
    viewList.append(viewData)
  return viewList 

def getDriversList():
  drivers = Driver.objects.all()
  completeResults = []
  
  for driver in drivers:
    infos = []
    completeResults.append(
      {
        "baseInfos": driver,
        "additionalInfos": infos,
        "position": 0
      }
    )
  # rank them
  for result in completeResults:
    result["position"] =  getRank(result, completeResults, "Points", True)
  
  # prepare additional columns types
  additionalColumnsNames = OrderedDict()
  

  # flatten te list for displaying
  viewList = []
  for result in completeResults:
    viewData = OrderedDict()
    viewData["firstName"] = result["baseInfos"].firstName, "longstr"
    viewData["lastName"] = result["baseInfos"].lastName, "longstr"
    for additionalColumnKey, additionalColumnType in additionalColumnsNames.items():
      for info in result["additionalInfos"]:
        if info.name == additionalColumnKey:
          viewData[info.name] = info.value, additionalColumnType
    viewList.append(viewData)
  return viewList 

def get_raceDetail(request, id: int):
  race = Race.objects.all().filter(pk=id).get()
  resultList = getRaceResult(id)
  return renderWithCommonData(request, 'frontend/race.html', {
    "race": race,
    "resultList": resultList,
    "title":  race.name +" - " + race.season.name
  })

def get_seasonStandingsTeams(request, id: int):
  resultList = getTeamStandings(id)
  return renderWithCommonData(request, 'frontend/result.html', {
    "resultList": resultList,
    "title": "Team standing - " + Season.objects.all().filter(pk=id).get().name
  })

def get_seasonStandingsDrivers(request, id: int):
  resultList = getDriversStandings(id)
  return renderWithCommonData(request, 'frontend/result.html', {
    "resultList": resultList,
    "title": "Drivers standing - " + Season.objects.all().filter(pk=id).get().name
  })

def get_DriversList(request):
  resultList = getDriversList()
  return renderWithCommonData(request, 'frontend/result.html', {
    "resultList": resultList,
    "title": "Drivers"
  })

def get_TeamsList(request):
  resultList = getTeamList()
  
  return renderWithCommonData(request, 'frontend/result.html', {
    "resultList": resultList,
    "title": "Teams"
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
  return JsonResponse({
    "entries": result,
    "controlSet": cameraControl.controlSet,
    "slotId": cameraControl.slotId,
    "cameraId":  cameraControl.cameraId,
    "commandId": cameraControl.id
  }, safe=False)

# Overlay control panel

def get_overlayControl(request, id: int):
  race = Race.objects.get(pk=id)
  entries = DriverEntry.objects.filter(teamEntry__season_id=race.season.id)
  allowed = [
    "currentDriver",
    "battle"
  ]
  if request.POST:
    for value in request.POST:
      if value in allowed:
        RaceOverlayControlSet.objects.filter(race_id=id).delete()
        overlay = RaceOverlayControlSet()
        overlay.race = race
        requested = request.POST[value]
        if " " in requested:
          # driver view requested
          overlay.slotId = -1
          overlay.controlSet = dumps({
            value: request.POST[value]
          })
        else:   
          overlay.controlSet = dumps({
            value: int(request.POST[value])
          })
          overlay.slotId =  int(request.POST[value])
        overlay.save()

  return render(request, "frontend/control/index.html", {'entries': entries, 'battle': range(1,len(entries) -1)})