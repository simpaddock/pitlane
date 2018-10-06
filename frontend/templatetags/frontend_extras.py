
from datetime import datetime, timedelta
from django import template

register = template.Library()
@register.filter
def time(seconds) -> str:
  if seconds == "-" or seconds == "":
    return ""
  seconds = float(seconds)
  hours, remainder = divmod(seconds, 3600)
  minutes, seconds = divmod(remainder, 60)
  return'{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

@register.filter
def index(list, i):
  if i >= len(list):
    return None
  return list[int(i)]