"""pitlane URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from frontend import views
from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from frontend.feeds import LatestEntriesFeed
from pitlane.settings import  LEAGUECONFIG

if LEAGUECONFIG["maintenance"]:
    urlpatterns = [
        url(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
        url(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
        url(r'^ckeditor/', include('ckeditor_uploader.urls')),
        path('feed/', LatestEntriesFeed()),
        path('admin/', admin.site.urls),
        path('robots.txt', views.get_robots),
        url(r'^.*', views.maintenance),
    ]
else:
    urlpatterns = [
        path('admin/', admin.site.urls),
        path('robots.txt', views.get_robots),
        path('', views.get_index),
        path('seasons/', views.get_seasonList),
        path('news/', views.get_news),
        path('about/', views.get_about),
        path('privacy/', views.get_privacy),
        path('imprint/', views.get_imprint),
        path('calendar/<int:id>/', views.get_iCalender),
        path('news/<int:id>/', views.get_SingleNews),
        path('generatenumberplate/', views.plate),
        path('incidents/<int:id>/', views.get_incidents),
        path('signup/', views.signUp),
        path('updatesignup/', views.signUpUpdate),
        path('withdrawsignup/', views.withdraw),
        path('submitlivery/', views.liverySubmission),
        path('driveroftheday/<int:id>/', views.driverOfTheDayVote),
        path('rules/', views.get_rules),
        path('incidentreport/', views.incidentReport),
        path('seasons/<int:id>/drivers/', views.get_seasonStandingsDrivers),
        path('seasons/<int:id>/teams/', views.get_seasonStandingsTeams),
        path('races/<int:id>/', views.get_raceDetail),
        path('driver/<int:id>/', views.getDriverStats),
        path('embed/video/youtube/<argument>/', views.embedYoutube),
        url(r'^ckeditor/', include('ckeditor_uploader.urls')),
        url(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
        url(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
        path('feed/', LatestEntriesFeed())
    ] 

