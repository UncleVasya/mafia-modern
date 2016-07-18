from collections import defaultdict
import json
import logging
from time import sleep
import datetime
from apps.game.models import ChatRoom, Game
from django.core.cache import cache
from channels import Group
from channels.auth import channel_session_user_from_http, channel_session_user
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


# TODO: make channel name and cache key to be the same,
# TODO: like so: cache['chat'] = {'members': {}}
GLOBAL_CHAT = 'chat'  # channel name
GLOBAL_CHAT_MEMBERS = 'chat_members'  # cache key

# channel name and cache key
GAME = 'game_'  # used by adding ID: 'game_ID'

# dict representing in what game user is currently in, if any:
# {'Vasya': 32, 'Petya': None}
GAME_BY_USER = 'game_by_user'  # cache_key


log = logging.getLogger(__name__)


def new_state():
    return {
        'players': [],
    }


# sends game list to the group or reply_channel
#
def send_game_list(channel):
    games = Game.objects.filter(status__in=['Created', 'Started'])
    game_list = []
    for game in games:
        state = cache.get(GAME + str(game.id), new_state())
        game_list.append({
            'id': game.id,
            'name': game.name,
            'level': game.level,
            'players_num': game.players_num,
            'players': state['players']
        })

    if isinstance(channel, str):
        channel = Group(channel)

    channel.send({
        'text': json.dumps({
            'game_list': game_list,
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
def ws_connect(message):
    Group(GLOBAL_CHAT).add(message.reply_channel)

    # send game list
    send_game_list(message.reply_channel)

    # send updated member list
    members = cache.get(GLOBAL_CHAT_MEMBERS, defaultdict(int))
    members[message.user.username] += 1  # connections number (user can open many tabs)
    cache.set(GLOBAL_CHAT_MEMBERS, members)

    Group(GLOBAL_CHAT).send({
        'text': json.dumps({
            'chat_members': members.keys()
        })
    })

    # send message history to new chat member
    room, _ = ChatRoom.objects.get_or_create(name=GLOBAL_CHAT)
    history = reversed(room.messages.order_by('-timestamp')[:50])

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
    if members[message.user.username] == 1:
        chat_message(GLOBAL_CHAT, {
            'text': 'User %s connected to the game.' % message.user.username,
            'sender': 'System',
        })

    # send greetings
    message.reply_channel.send({
        'text': json.dumps({
            'text': 'Welcome to the Mafia!',
            'sender': 'System',
            'timestamp': timezone.now().isoformat()
        })
    })

    log.debug('Chat connect. Client: %s:%s',
              message['client'][0], message['client'][1])


def game_add_user(game_id, message):
    # check if game exists
    # and not yet started or canceled
    # TODO: do it via cache instead of DB?
    try:
        game = Game.objects.get(id=game_id)
        if game.status != 'Created':
            return
    except ObjectDoesNotExist:
        return

    # update game state
    game_cache_key = GAME + str(game_id)
    state = cache.get(game_cache_key, new_state())
    state['players'].append(message.user.username)
    cache.set(game_cache_key, state)

    # update user game presence
    game_by_user = cache.get(GAME_BY_USER, defaultdict(int))
    game_by_user[message.user.username] = game_id
    cache.set(GAME_BY_USER, game_by_user)

    # send updated game list to users
    send_game_list(GLOBAL_CHAT)

    message.reply_channel.send({
        'text': json.dumps({
            'text': 'You joined %s.' % game.name,
            'sender': 'System',
            'timestamp': timezone.now().isoformat()
        })
    })


def user_leave_game(message):
    # check if user is currently in game
    game_by_user = cache.get(GAME_BY_USER, defaultdict(int))
    game_id = game_by_user[message.user.username]
    if not game_id:
        return

    # update user game presence
    game_by_user[message.user.username] = None
    cache.set(GAME_BY_USER, game_by_user)

    # update game state
    game_cache_key = GAME + str(game_id)
    state = cache.get(game_cache_key)
    state['players'].remove(message.user.username)
    cache.set(game_cache_key, state)

    game = Game.objects.get(id=game_id)
    message.reply_channel.send({
        'text': json.dumps({
            'text': 'You left %s.' % game.name,
            'sender': 'System',
            'timestamp': timezone.now().isoformat()
        })
    })

    if not state['players']:
        # all players left, cancel this game
        cache.delete(game_cache_key)
        game.status = 'Canceled'
        game.save()

        chat_message(GLOBAL_CHAT, {
            'text': '%s was canceled cause all players left.' % game.name,
            'sender': 'System',
        })

    # send updated game list to users
    send_game_list(GLOBAL_CHAT)


# Connected to websocket.receive
@channel_session_user
def ws_message(message):
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

    if command == 'chat_msg':
        chat_message(GLOBAL_CHAT, {
            'text': data['text'],
            'sender': message.user.username
        })

    elif command in ['game_create', 'game_join']:
        # check that user is not currently in game
        game_by_user = cache.get(GAME_BY_USER, defaultdict(int))
        current_game = game_by_user.get(message.user.username, None)
        if current_game:
            # TODO: add name info to game cache so I don't need to query DB here
            game = Game.objects.get(id=current_game)
            message.reply_channel.send({
                'text': json.dumps({
                    'text': 'You are already in %s.' % game.name,
                    'sender': 'System',
                    'timestamp': timezone.now().isoformat()
                })
            })
            return

        if command == 'game_create':
            games_today = Game.objects.filter(
                timestamp__gte=datetime.date.today()
            ).count()

            game = Game.objects.create(
                name='game%d' % (games_today + 1),
                players_num=7,
                type='Normal',
                created_by=message.user.username,
            )
            chat_message(GLOBAL_CHAT, {
                'text': '%s was created.' % game.name,
                'sender': 'System',
            })

            game_add_user(game.id, message)
        else:  # game_join
            game_add_user(data['id'], message)

    elif command == 'game_leave':
        user_leave_game(message)


# Connected to websocket.disconnect
@channel_session_user
def ws_disconnect(message):
    Group(GLOBAL_CHAT).discard(message.reply_channel)

    # check the number of clients this user still has
    # and if zero, then remove him from members list
    members = cache.get(GLOBAL_CHAT_MEMBERS, defaultdict(int))
    members[message.user.username] -= 1
    if members[message.user.username] <= 0:  # no connections left
        del members[message.user.username]

        # notify other members about user disconnect
        chat_message(GLOBAL_CHAT, {
            'text': 'User %s disconnected from the game.' % message.user.username,
            'sender': 'System',
        })

        # send updated members list
        Group(GLOBAL_CHAT).send({
            'text': json.dumps({
                'chat_members': members.keys()
            })
        })
    cache.set(GLOBAL_CHAT_MEMBERS, members)
