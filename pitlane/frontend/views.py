from django.shortcuts import render, HttpResponse
from collections import OrderedDict

from .models import NewsArticle, Season, Race, TeamEntry, Track, RaceResult, DriverRaceResult, DriverRaceResultInfo, DriverEntry, Driver, Team
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from json import dumps
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import filetype
LIST_DATA_RACE = "race"
LIST_DATA_TEAM_STANDINGS = "teams"
LIST_DATA_DRIVERS_STANDINGS = "drivers"
LIST_DATA_DRIVERS ="listdrivers"
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


def getSeasonDrivers(seasonId: int) -> list:
  teams = TeamEntry.objects.all().filter(season_id=seasonId)
  drivers = list()
  for team in teams:
    teamDrivers = DriverEntry.objects.all().filter(teamEntry_id=team.id)
    for driver in teamDrivers:
      drivers.append(driver.id) # FIXME: full object leads to json error
  return drivers


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
  
  seasonsJSON = dumps(resultList, cls=DjangoJSONEncoder)
  return renderWithCommonData(request, 'frontend/seasons.html', {
    "seasons": seasonList,
    "seasonsJSON": seasonsJSON
  })

def getRank(row, haystack, columnToSearch: str, reverse=False) -> int:
  allElements = []
  needle = None
  column: DriverRaceResultInfo
  for element in haystack: 
    for column in element["additionalInfos"]:
      if column.name == columnToSearch:
        allElements.append(column.value)
      if element == row:
        needle = column.value
  allElements.sort(reverse=reverse)
  if needle == None or needle not in allElements:
    return len(allElements)
  return allElements.index(needle) + 1


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
  # rank them
  for result in completeResults:
    result["position"] =  getRank(result, completeResults, "Position")
  
  # prepare additional columns types
  additionalColumnsNames = OrderedDict()
  additionalColumnsNames["Laps"] = "int"
  additionalColumnsNames["Stops"] = "int"
  additionalColumnsNames["Time"] = "time"
  additionalColumnsNames["Avg"] = "float"
  additionalColumnsNames["Points"] = "int"
  additionalColumnsNames["Status"] = "status"
  additionalColumnsNames["ControlAndAids"] = "params"

  # flatten te list for displaying
  viewList = []
  for result in completeResults:
    viewData = OrderedDict()
    viewData["position"] = result["position"], "position"
    viewData["firstName"] = result["baseInfos"].driverEntry.driver.firstName, "longstr"
    viewData["lastName"] = result["baseInfos"].driverEntry.driver.lastName, "longstr"
    viewData["team"] = result["baseInfos"].driverEntry.teamEntry.team.name, "longstr"
    viewData["teamlogo"] = result["baseInfos"].driverEntry.teamEntry.team.logo, "image"
    viewData["vehicle"] = result["baseInfos"].driverEntry.teamEntry.vehicle  + "#" + result["baseInfos"].driverEntry.driverNumberFormat.format(result["baseInfos"].driverEntry.driverNumber), "raw"
    for additionalColumnKey, additionalColumnType in additionalColumnsNames.items():
      for info in result["additionalInfos"]:
        if info.name == additionalColumnKey:
          viewData[info.name] = info.value, additionalColumnType
    viewList.append(viewData)
  return viewList

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
        if info.name == additionalColumnKey:
          viewData[info.name] = info.value, additionalColumnType
    viewList.append(viewData)
  return viewList

def getDriversStandings(id: int):
  allTeams = TeamEntry.objects.all().filter(season_id=id)
  completeResults = []
  # collect all infos
  for team in allTeams:
    driverEntries = DriverEntry.objects.all().filter(teamEntry_id=team.id)
 
    for driverEntry in driverEntries:
      # get race results
      races = DriverRaceResult.objects.filter(driverEntry_id=driverEntry.id)
      infos = []
      allPoints = 0
      for race in races:
        driverPoints = DriverRaceResultInfo.objects.filter(driverRaceResult_id=race.id).filter(name='Points')
        for point in driverPoints:
          # add per race sum
          pointColumn = DriverRaceResultInfo()
          pointColumn.name = race.raceResult.race.name
          pointColumn.value = int(point.value)
          allPoints = allPoints + int(point.value)
          infos.append(pointColumn)
        
      # add a sum column
      pointColumn = DriverRaceResultInfo()
      pointColumn.name = "Points"
      pointColumn.value = allPoints
      infos.append(pointColumn)
      # append to complete list
      completeResults.append(
        {
          "baseInfos": driverEntry,
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
    viewData["firstName"] = result["baseInfos"].driver.firstName, "longstr"
    viewData["lastName"] = result["baseInfos"].driver.lastName, "longstr"
    for additionalColumnKey, additionalColumnType in additionalColumnsNames.items():
      for info in result["additionalInfos"]:
        if info.name == additionalColumnKey:
          viewData[info.name] = info.value, additionalColumnType
    viewList.append(viewData)
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
  return renderWithCommonData(request, 'frontend/result.html', {
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