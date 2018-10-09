from django.contrib import admin
from django.utils.html import format_html
from .models import Incident, Registration, Track, Race, Driver, Team, Country, DriverEntry, TeamEntry, RaceResult, DriverRaceResult, Season, DriverRaceResultInfo, NewsArticle, RaceOverlayControlSet

class DriverEntryAdmin(admin.ModelAdmin):
    list_display = ['toString']

    def toString(self, obj):
      return format_html("#{0}: {1}, {2}: {3}".format(str(obj.driverNumberFormat).format(obj.driverNumber), obj.driver.lastName, obj.driver.firstName, obj.teamEntry.team.name))
    
    toString.short_description = 'Driver entry'



class RaceResultAdmin(admin.ModelAdmin):
  readonly_fields = ('results',)

class DriverRaceResultAdmin(admin.ModelAdmin):
  actions = ['disqualify', 'undisqualify', 'undisqualify_dnf']

  def disqualify(modeladmin, request, queryset):
    for driver in queryset:
      resultInfo = DriverRaceResultInfo.objects.filter(name='finishstatus', driverRaceResult_id=driver.id).update(value='dsq')
  disqualify.short_description = "Disqualify Driver"
  def undisqualify(modeladmin, request, queryset):
    for driver in queryset:
      resultInfo = DriverRaceResultInfo.objects.filter(name='finishstatus', driverRaceResult_id=driver.id).update(value='Finished Normally')
  undisqualify.short_description = "Un-Disqualify Driver (Finished Normally)"
  def undisqualify_dnf(modeladmin, request, queryset):
    for driver in queryset:
      resultInfo = DriverRaceResultInfo.objects.filter(name='finishstatus', driverRaceResult_id=driver.id).update(value='dnf')
  undisqualify_dnf.short_description = "Un-Disqualify Driver (DNF)"

class RegistrationAdmin(admin.ModelAdmin):
  readonly_fields = ('downloadLink',)

admin.site.register(Track)
admin.site.register(Race)
admin.site.register(Driver)
admin.site.register(Team)
admin.site.register(DriverEntry, DriverEntryAdmin)
admin.site.register(TeamEntry)
admin.site.register(RaceResult, RaceResultAdmin)
admin.site.register(DriverRaceResult,DriverRaceResultAdmin)
admin.site.register(Season)
admin.site.register(DriverRaceResultInfo)
#admin.site.register(RaceOverlayControlSet)
admin.site.register(NewsArticle)
admin.site.register(Country)
admin.site.register(Incident)
admin.site.register(Registration, RegistrationAdmin)

from pitlane.settings import LEAGUECONFIG

admin.site.site_header = LEAGUECONFIG["name"]
admin.site.site_title = "SimPaddock"
admin.site.index_title = "" # we don't need a second title..
