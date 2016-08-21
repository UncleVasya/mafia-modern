from apps.game.urls import GAME_URL
from channels.routing import route, include
from apps.game.consumers import lobby, game


lobby_routing = [
    route('websocket.connect', lobby.ws_connect),
    route('websocket.receive', lobby.ws_message),
    route('websocket.disconnect', lobby.ws_disconnect),
]

game_routing = [
    route('websocket.connect', game.ws_connect),
    route('websocket.receive', game.ws_message),
    route('websocket.disconnect', game.ws_disconnect)
]

channel_routing = [
    include(lobby_routing, path=r'^/$'),
    include(game_routing, path=r'^/' + GAME_URL[1:]),  # '^games' replaced with '^/games'
]
