from frontend.models import Race, NewsArticle
from django import template
from datetime import datetime
from urllib.parse import urljoin
from pitlane.settings import LEAGUECONFIG

register = template.Library()
## context based tags, e. g. next race..

@register.simple_tag
def next_championship():
  nextRace = Race.objects.filter(season__isRunning=True, endDate__gt=datetime.now()).order_by("startDate").first()
  if nextRace is None:
    return None
  championship = nextRace.season
  championship.nextRace = nextRace
  return championship

@register.filter
def share_buttons(article: NewsArticle):
  urlToUse = urljoin(LEAGUECONFIG["url"], '/news/'+ str(article.id)) # ",/" does not work 
  titleToUse = article.title
  shareButtons = [
    {
      "name": "Twitter",
      "icon": "fab fa-twitter-square",
      "url": "https://twitter.com/intent/tweet?url=" + urlToUse + '&text=' + titleToUse
    },
    {
      "name": "Facebook",
      "icon": "fab fa-facebook-square",
      "url": "http://www.facebook.com/sharer.php?u=" + urlToUse
    },
    {
      "name": "reddit",
      "icon": "fab fa-reddit-square",
      "url": "https://reddit.com/submit?url=" + urlToUse + '&title=' + titleToUse
    },
    {
      "name": "reddit",
      "icon": "fab fa-get-pocket",
      "url": "https://getpocket.com/edit?url=" +urlToUse
    },
    {
      "name": "reddit",
      "icon": "fab fa-flipboard",
      "url": "https://share.flipboard.com/bookmarklet/popout?v=2&title=" + titleToUse + '&url=' + urlToUse
    },
    {
      "name": "pinterest",
      "icon": "fab fa-pinterest",
      "url": "http://pinterest.com/pin/create/button/?url=" + urlToUse
    },
    {
      "name": "RSS",
      "icon": "fas fa-rss",
      "url": "/feed"
    }
  ]
  return shareButtons
