from nameparser import HumanName
from xml.dom import minidom
import frontend.models as dbModels
from django.db import models

def calculateRFactorResult(self, *args, **kwargs):
    dbModels.DriverRaceResultInfo.objects.filter(driverRaceResult__raceResult_id=self.id).delete()
    dbModels.DriverRaceResult.objects.filter(raceResult_id=self.id).delete()

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
      teamName = rawData["TeamName"]
      carNumber = rawData["CarNumber"]
      vehicle = rawData["CarClass"]
      
      fittingTeams = dbModels.Team.objects.all().filter(name=teamName)
      if fittingTeams.count() == 0:
        # create new team
        newTeam = Team()
        newTeam.name = teamName
        newTeam.save()


      
      team = dbModels.Team.objects.get(name=teamName) 
      
      if dbModels.TeamEntry.objects.filter(season_id=self.race.season.id, team_id=team.id).count() == 0:
        # team is existing -> get new entry if needed
        newTeamEntry = dbModels.TeamEntry()
        newTeamEntry.team = Team.objects.all().filter(name=teamName).get()
        newTeamEntry.vehicle = vehicle
        newTeamEntry.season = self.race.season
        newTeamEntry.save()

      teamEntry = dbModels.TeamEntry.objects.filter(season_id=self.race.season.id, team=team).get()
      # 2. find Driver
      # concat name parts if the driver is e. g. a spanish speaking human
      name = HumanName(rawData["Name"])
      firstName = name.first
      if name.middle != "":
        lastName = name.middle + " " + name.last
      else:
        lastName = name.last
      fittingDrivers = dbModels.Driver.objects.all().filter(firstName=firstName,lastName=lastName)

      driver=None
      if fittingDrivers.count() == 0:
        # create new driver
        driver = dbModels.Driver()
        driver.firstName = firstName
        driver.lastName = lastName
        driver.country = Country.objects.first()
        driver.save()
        print("Created {0}, {1}".format(lastName, firstName))
      
      driver = dbModels.Driver.objects.filter(firstName=firstName,lastName=lastName).get()
      if dbModels.DriverEntry.objects.filter(driver_id=driver, teamEntry_id=teamEntry.id).count() == 0:
        # give the driver a new team entry 
        driverEntry = dbModels.DriverEntry()
        driverEntry.driver = dbModels.Driver.objects.filter(firstName=firstName,lastName=lastName).get()
        driverEntry.teamEntry = teamEntry
        driverEntry.driverNumber = carNumber
        driverEntry.driverNumberFormat = "{0}"
        driverEntry.save()
        print("--> New driver entry: {0} for {1}".format(carNumber, teamEntry))
        
      test =dbModels.DriverEntry.objects.all()
      """
      I may run into a bug here. Django does not return anything useful with filter()
      """
      driverEntry = None
      for t in test:
        if t.driver == driver and t.teamEntry.season == self.race.season:
         driverEntry = t
         break

      driverRaceResult = dbModels.DriverRaceResult()
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
          driverRaceResultInfo = dbModels.DriverRaceResultInfo()
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
        driverRaceResultInfo = dbModels.DriverRaceResultInfo()
        driverRaceResultInfo.driverRaceResult = driverRaceResult
        driverRaceResultInfo.name = "avg"
        driverRaceResultInfo.value = round(((trackLength/1000)*runLaps)/ (float(rawData["Time"])/60/60),2)
        driverRaceResultInfo.infoType = "str"
        driverRaceResultInfo.save()