from django.contrib import admin
from django.utils.html import format_html
from .models import Track, Race, Driver, Team, Country, DriverEntry, TeamEntry, RaceResult, DriverRaceResult, Season, DriverRaceResultInfo, NewsArticle, RaceOverlayControlSet

class DriverEntryAdmin(admin.ModelAdmin):
    list_display = ['toString']

    def toString(self, obj):
      return format_html("#{0}: {1}, {2}: {3}".format(str(obj.driverNumberFormat).format(obj.driverNumber), obj.driver.lastName, obj.driver.firstName, obj.teamEntry.team.name))
    
    toString.short_description = 'Driver entry'

class RaceResultAdmin(admin.ModelAdmin):
   readonly_fields = ('results',)

admin.site.register(Track)
admin.site.register(Race)
admin.site.register(Driver)
admin.site.register(Team)
admin.site.register(DriverEntry, DriverEntryAdmin)
admin.site.register(TeamEntry)
admin.site.register(RaceResult, RaceResultAdmin)
#admin.site.register(DriverRaceResult)
admin.site.register(Season)
#admin.site.register(DriverRaceResultInfo)
#admin.site.register(RaceOverlayControlSet)
admin.site.register(NewsArticle)
admin.site.register(Country)

from pitlane.settings import LEAGUECONFIG

admin.site.site_header = LEAGUECONFIG["name"]
admin.site.site_title = "SimPaddock"
admin.site.index_title = "" # we don't need a second title..
