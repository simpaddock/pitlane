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


urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', views.get_robots, name='robots.txt'),
    path('', views.get_index, name='index'),
    path('seasons/', views.get_seasonList, name='seasons'),
    path('news/', views.get_news, name='news'),
    path('about/', views.get_about, name='about'),
    path('privacy/', views.get_privacy, name='privacy'),
    path('imprint/', views.get_imprint, name='imprint'),
    path('news/<int:id>/', views.get_SingleNews, name='singleNews'),
    path('racebanner/<int:id>/', views.get_raceBanner, name='get_raceBanner'),
    path('signup/', views.signUp, name='signup'),
    path('rules/', views.get_rules, name='get_rules'),
    path('incidentreport/', views.incidentReport, name='incident'),
    path('seasons/<int:id>/drivers/', views.get_seasonStandingsDrivers, name='season'),
    path('seasons/<int:id>/teams/', views.get_seasonStandingsTeams, name='season'),
    path('races/<int:id>/', views.get_raceDetail, name='raceDetail'),
    path('api/entries/<int:id>', views.get_raceData, name='get_raceData'),
    path('control/<int:id>', views.get_overlayControl, name='get_raceData'),
    url(r'^ckeditor/', include('ckeditor_uploader.urls'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
