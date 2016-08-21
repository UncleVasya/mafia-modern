from collections import defaultdict
import json
import logging
from time import sleep
import datetime
from apps.game.consumers.lobby import GAME
from apps.game.models import ChatRoom, Game
from django.core.cache import cache
from channels import Group
from channels.auth import channel_session_user_from_http, channel_session_user
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


log = logging.getLogger(__name__)


# sends client his username and status
def send_user_status(message):
    username = message.user.username

    message.reply_channel.send({
        'text': json.dumps({
            'user': username,
        })
    })


# sends message to the room and saves it do DB
def chat_message(room, message):
    log.debug('Chat message. Message: %s', message)

    room_obj = ChatRoom.objects.get(name=room)
    msg = room_obj.messages.create(**message)

    Group(room).send({
        'text': json.dumps({
            'text': msg.text,
            'sender': msg.sender,
            'timestamp': msg.timestamp.isoformat()
        })
    })


# Connected to websocket.connect
@channel_session_user_from_http
def ws_connect(message, year, month, day, slug):
    # get game object using url parameters
    date = datetime.datetime(year=int(year), month=int(month), day=int(day))
    game = Game.objects.filter(
        timestamp__gte=date,
        timestamp__lt=date + datetime.timedelta(days=1)
    ).get(name=slug)

    game_key = GAME + str(game.id)
    message.channel_session['game_id'] = str(game.id)
    Group(game_key).add(message.reply_channel)

    send_user_status(message)

    # update player clients num
    state = cache.get(game_key)
    state['players'][message.user.username]['clients'] += 1
    cache.set(game_key, state)

    # send message history to new chat member
    room, _ = ChatRoom.objects.get_or_create(name=game_key)
    history = reversed(room.messages.order_by('-timestamp'))

    for msg in history:
        message.reply_channel.send({
            'text': json.dumps({
                'text': msg.text,
                'sender': msg.sender,
                'timestamp': msg.timestamp.isoformat()
            })
        })
        sleep(0.01)  # to not overflood websocket

    # if this is his first client, notify others about connected user
    if state['players'][message.user.username]['clients'] == 1:
        Group(game_key).send({
            'text': json.dumps({
                'players': state['players']
            })
        })

    # send greetings
    message.reply_channel.send({
        'text': json.dumps({
            'text': 'You are in %s' % game.name,
            'sender': 'System',
            'timestamp': timezone.now().isoformat()
        })
    })

    log.debug('Game connect. Client: %s:%s',
              message['client'][0], message['client'][1])


# Connected to websocket.receive
@channel_session_user
def ws_message(message, **kwargs):
    if not message.user.is_active:
        return

    try:
        data = json.loads(message['text'])
        log.debug("Got ws message: %s", data)
    except ValueError:
        log.debug("ws message isn't json text: %s", message['text'])
        return

    command = data.get('command', None)
    if not command:
        log.debug("ws message unexpected format: %s", data)
        return

    game_key = GAME + message.channel_session['game_id']

    if command == 'chat_msg':
        chat_message(game_key, {
            'text': data['text'],
            'sender': message.user.username
        })


# Connected to websocket.disconnect
@channel_session_user
def ws_disconnect(message, **kwargs):
    game_key = GAME + message.channel_session['game_id']

    Group(game_key).discard(message.reply_channel)

    # update player clients num
    state = cache.get(game_key)
    player = state['players'][message.user.username]
    player['clients'] -= 1
    cache.set(game_key, state)

    # if no connections left from this player, notify others about disconnect
    if player['clients'] <= 0:
        # TODO: replace chat message with clock icon of frontend
        chat_message(game_key, {
            'text': 'User %s disconnected from the game.' % message.user.username,
            'sender': 'System',
        })

        # send updated members list
        Group(game_key).send({
            'text': json.dumps({
                'chat_members': state['players']
            })
        })
