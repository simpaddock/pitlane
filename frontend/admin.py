from django.contrib import admin

from .models import Track, Race, Driver, Team, Country, DriverEntry, TeamEntry, RaceResult, DriverRaceResult, Season, DriverRaceResultInfo, NewsArticle

admin.site.register(Track)
admin.site.register(Race)
admin.site.register(Driver)
admin.site.register(Team)
admin.site.register(Country)
admin.site.register(DriverEntry)
admin.site.register(TeamEntry)
admin.site.register(RaceResult)
admin.site.register(DriverRaceResult)
admin.site.register(Season)
admin.site.register(DriverRaceResultInfo)
admin.site.register(NewsArticle)

from pitlane.settings import LEAGUECONFIG

admin.site.site_header = LEAGUECONFIG["name"]
admin.site.site_title = "SimPaddock"
admin.site.index_title = LEAGUECONFIG["name"]
