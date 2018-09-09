from django.apps import AppConfig

from pitlane.settings import LEAGUECONFIG

class FrontendConfig(AppConfig):
    name = 'frontend'
    verbose_name = LEAGUECONFIG["name"]
