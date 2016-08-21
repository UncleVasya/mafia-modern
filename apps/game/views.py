from apps.game.models import Game
from django.views.generic import TemplateView, DateDetailView, TodayArchiveView, YearArchiveView


class LobbyView(TemplateView):
    template_name = 'game/lobby.html'


class GameView(DateDetailView):
    model = Game
    slug_field = 'name'
    date_field = 'timestamp'
    month_format = '%m'
    template_name = 'game/game.html'


class GamesTodayView(TodayArchiveView):
    model = Game
    date_field = 'timestamp'


class GamesYearView(YearArchiveView):
    model = Game
    make_object_list = True
    date_field = 'timestamp'