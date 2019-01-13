import matplotlib.pyplot as plt
import base64
from io import BytesIO
from django.db.models import Model
from frontend.models import  TeamEntry, DriverEntry, DriverRaceResultInfo, DriverRaceResult, Race
from pitlane.settings import LEAGUECONFIG, COLUMNS
from collections import OrderedDict
from functools import reduce
from django.core.serializers.json import DjangoJSONEncoder
import zipfile
from os.path import basename
from unidecode import unidecode 

def generateSparkline(data, figsize=(4, 0.25), **kwags):
  data = list(data)
  # based on https://markhneedham.com/blog/2017/09/23/python-3-create-sparklines-using-matplotlib/

  fig, ax = plt.subplots(1, 1, figsize=figsize, **kwags)
  ax.plot(data)
  for k,v in ax.spines.items():
      v.set_visible(False)
  ax.set_xticks([])
  ax.set_yticks([])

  plt.plot(len(data) - 1, data[len(data) - 1], color='white', linestyle='dashed', marker='o',markerfacecolor='white', markersize=0)

  img = BytesIO()
  plt.savefig(img, transparent=True, bbox_inches='tight')
  img.seek(0)
  plt.close()

  return base64.b64encode(img.read()).decode("UTF-8")


def getChildValue(haystack, needle): # mostly needed for driver and team results, race
  parts = needle.split(".")
  value = haystack
  for part in parts:
    # last parent is dict or object -> extract children
    if isinstance(value, dict):
      value = value[part]
    elif isinstance(value, Model):
      value = getattr(value, part)
    elif isinstance(value, object):
      value = value.__dict__[part]
  return value

def getSeasonDrivers(seasonId: int) -> list:
  teams = TeamEntry.objects.all().filter(season_id=seasonId)
  drivers = list()
  for team in teams:
    teamDrivers = DriverEntry.objects.all().filter(teamEntry_id=team.id)
    for driver in teamDrivers:
      drivers.append(driver) # FIXME: full object leads to json error
  return drivers

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

def getClientIP(request):
  x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
  if x_forwarded_for:
      ip = x_forwarded_for.split(',')[0]
  else:
      ip = request.META.get('REMOTE_ADDR')
  return ip

class JSONEncoder(DjangoJSONEncoder): # for json serializing
    def default(self, o):
        return str(o)

def getDriverName(firstName: str, lastName:str) -> str:
  from re import sub
  return sub(r"[^a-zA-Z\s:]","",unidecode(firstName) + " " + unidecode(lastName))


def generateServerData(queryset):
  zipf = zipfile.ZipFile('Python.zip', 'w', zipfile.ZIP_DEFLATED)
  for key, tuple in enumerate(queryset):
    # add skin file
    driverName = getDriverName(tuple.firstName, tuple.lastName)

    skinFile =  "/" + driverName + "/alt_" + str(tuple.number) + ".dds"
    sourceSkinFile = tuple.skinFile.path
    zipf.write(sourceSkinFile, skinFile)
    rcdTemplate = """//[[gMa1.002f (c)2016    ]] [[            ]]
GT3
{{
  {name}
  {{
    Team = {team}
    Component = {carName}
    Skin = alt_{number}.dds
    VehFile = {vehfile}
    Description = {description}
    Number = {number}
  }}
}}"""
    rcdTemplateContent = rcdTemplate.format(name=driverName, number=tuple.number,description=tuple.teamName + " #" + str(tuple.number), team=tuple.teamName,vehfile=tuple.vehicleClass.vehicleClass,carName=tuple.vehicleClass.displayName)
    zipf.writestr(str(key) + ".rcd", rcdTemplateContent)

    
  zipf.close()
