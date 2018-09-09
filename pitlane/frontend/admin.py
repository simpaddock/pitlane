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