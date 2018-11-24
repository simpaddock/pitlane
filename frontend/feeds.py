from django.contrib.syndication.views import Feed
from django.urls import reverse
from frontend.models import NewsArticle
from pitlane.settings import LEAGUECONFIG

class LatestEntriesFeed(Feed):
    title = LEAGUECONFIG["name"]
    link = "/news/"

    def items(self):
      return NewsArticle.objects.filter(isDraft=False).order_by('-date')[:5]

    def item_title(self, item):
      return item.title

    def item_description(self, item):
      return item.text

    def item_link(self, item):
      return "/news/{0}/".format(item.id)
    
    def item_pubdate(self, item):
      return item.date