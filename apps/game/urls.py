from django.conf.urls import url
from apps.game.views import LobbyView, GameView, GamesTodayView, GamesYearView


GAME_URL = r'^games/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<slug>\w+)/$'


urlpatterns = [
    url(r'^$', LobbyView.as_view(), name='index'),

    url(GAME_URL, GameView.as_view(), name='game'),

    url(r'^games/today/$', GamesTodayView.as_view(), name='games_today'),
    url(r'^games/(?P<year>[0-9]{4})/$', GamesYearView.as_view(), name='games_year')
]
