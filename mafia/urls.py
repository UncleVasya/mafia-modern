from django.conf.urls import url, include
from django.contrib import admin


urlpatterns = [
    url(r'^', include('apps.game.urls', namespace='game')),
    url(r'^', include('django.contrib.auth.urls')),
    url(r'^admin/', admin.site.urls),
]
