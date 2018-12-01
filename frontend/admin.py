from django.contrib import admin
from django.utils.html import format_html
from .models import DriverOfTheDayVote, Upload, GenericPrivacyAccept, RegistrationStatus, TextBlock,Incident, Registration, Track, Race, Driver, Team, Country, DriverEntry, TeamEntry, RaceResult, DriverRaceResult, Season, DriverRaceResultInfo, NewsArticle
from django.db.models.signals import post_save
from django.core.cache import cache
from django.dispatch import receiver
from django.contrib import messages
from django.utils.html import mark_safe
from django.db.models import Count

class DriverEntryAdmin(admin.ModelAdmin):
  list_display = ['toString']

  def toString(self, obj):
    return format_html("#{0}: {1}, {2}: {3}".format(str(obj.driverNumberFormat).format(obj.driverNumber), obj.driver.lastName, obj.driver.firstName, obj.teamEntry.team.name))
  
  toString.short_description = 'Driver entry'
  def get_queryset(self, request):
    qs = super(DriverEntryAdmin, self).get_queryset(request)
    return qs.filter(teamEntry__season__isRunning=True)

class TeamEntryAdmin(admin.ModelAdmin):
  def get_queryset(self, request):
    qs = super(TeamEntryAdmin, self).get_queryset(request)
    return qs.filter(season__isRunning=True)

class RaceResultAdmin(admin.ModelAdmin):
  readonly_fields = ('results',)
  def get_queryset(self, request):
    qs = super(RaceResultAdmin, self).get_queryset(request)
    return qs.filter(race__season__isRunning=True)

  def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
      field = super(RaceResultAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
      if db_field.name == 'race':
        field.queryset = field.queryset.filter(season__isRunning=True).order_by("startDate")

      return field

class DriverOfTheDayVoteAdmin(admin.ModelAdmin):
  actions = ['getResult']
  def changelist_view(self, request, extra_context=None):
    try:
        action = self.get_actions(request)[request.POST['action']][0]
        action_acts_on_all = action.acts_on_all
    except (KeyError, AttributeError):
        action_acts_on_all = False

    if action_acts_on_all:
        post = request.POST.copy()
        post.setlist(admin.helpers.ACTION_CHECKBOX_NAME,
                     self.model.objects.values_list('id', flat=True))
        request.POST = post

    return admin.ModelAdmin.changelist_view(self, request, extra_context)
    
  def getResult(modeladmin, request, queryset):
    voteResult = DriverOfTheDayVote.objects.values('driver').annotate(votes=Count('driver')).order_by("-votes")
    if voteResult.count() ==0:
      messages.error(request, "Not enought votes")
    else:
      message = ""
      for driverVote in voteResult:
        driver = Driver.objects.get(id=driverVote["driver"])
        message = message + "{0}: {1}x<br>".format(driver, driverVote["votes"])
      messages.info(request, mark_safe(message))
  getResult.short_description = "Get Driver of the day vote result"
  getResult.acts_on_all = True


class RaceAdmin(admin.ModelAdmin):
  readonly_fields = ('banner',)
  def get_queryset(self, request):
    qs = super(RaceAdmin, self).get_queryset(request)
    return qs.filter(season__isRunning=True)
class DriverRaceResultAdmin(admin.ModelAdmin):
  readonly_fields = ('resultDetails',) 
  actions = ['disqualify', 'undisqualify', 'undisqualify_dnf', 'addBonusPoint', 'removeBonusPoint']
  def get_queryset(self, request):
    qs = super(DriverRaceResultAdmin, self).get_queryset(request)
    return qs.filter(raceResult__race__season__isRunning=True)

  def disqualify(modeladmin, request, queryset):
    for driver in queryset:
      resultInfo = DriverRaceResultInfo.objects.filter(name='finishstatus', driverRaceResult_id=driver.id).update(value='dsq')
  disqualify.short_description = "Disqualify Driver"

  def addBonusPoint(modeladmin, request, queryset):
    for driver in queryset:
      bonus = DriverRaceResultInfo()
      bonus.driverRaceResult = driver
      bonus.name ="bonuspoints"
      bonus.value = "1"
      bonus.infoType = "int"
      bonus.save()
  addBonusPoint.short_description = "Grant 1 bonus point"

  def removeBonusPoint(modeladmin, request, queryset):
    for driver in queryset:
      DriverRaceResultInfo.objects.filter(name='bonuspoints', driverRaceResult_id=driver.id).delete()
  removeBonusPoint.short_description = "Remove bonus points"

  def undisqualify(modeladmin, request, queryset):
    for driver in queryset:
      resultInfo = DriverRaceResultInfo.objects.filter(name='finishstatus', driverRaceResult_id=driver.id).update(value='Finished Normally')
  undisqualify.short_description = "Un-Disqualify Driver (Finished Normally)"

  def undisqualify_dnf(modeladmin, request, queryset):
    for driver in queryset:
      resultInfo = DriverRaceResultInfo.objects.filter(name='finishstatus', driverRaceResult_id=driver.id).update(value='dnf')
  undisqualify_dnf.short_description = "Un-Disqualify Driver (DNF)"


class RegistrationAdmin(admin.ModelAdmin):
  readonly_fields = ('downloadLink', 'gdprAccept', 'copyrightAccept')  
  def get_queryset(self, request):
    qs = super(RegistrationAdmin, self).get_queryset(request)
    return qs.filter(season__isRunning=True)

class IncidentAdmin(admin.ModelAdmin):
  def get_queryset(self, request):
    qs = super(IncidentAdmin, self).get_queryset(request)
    return qs.filter(race__season__isRunning=True)

class GenericPrivacyAcceptAdmin(admin.ModelAdmin):
  def get_readonly_fields(self, request, obj=None):
    return self.fields or [f.name for f in self.model._meta.fields]

[admin.site.register(*models) for models in [
  (Track,),
  (Race, RaceAdmin),
  (Driver,),
  (Team,),
  (DriverEntry, DriverEntryAdmin),
  (TeamEntry, TeamEntryAdmin),
  (RaceResult, RaceResultAdmin),
  (DriverRaceResult,DriverRaceResultAdmin),
  (Season,),
  (DriverRaceResultInfo,),
  (NewsArticle,),
  (Country,),
  (Incident, IncidentAdmin),
  (TextBlock,),
  (Upload,),
  (Registration, RegistrationAdmin),
  (RegistrationStatus,),
  (DriverOfTheDayVote,DriverOfTheDayVoteAdmin),
  (GenericPrivacyAccept,GenericPrivacyAcceptAdmin),
]]

@receiver(post_save)
def clear_the_cache(**kwargs):
  cache.clear() # clear cache on save..

from pitlane.settings import LEAGUECONFIG

admin.site.site_header = LEAGUECONFIG["name"]
admin.site.site_title = "SimPaddock"
admin.site.index_title = "" # we don't need a second title..