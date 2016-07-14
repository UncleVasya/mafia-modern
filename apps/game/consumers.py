from collections import defaultdict
import json
import logging
from time import sleep, timezone
from apps.game.models import ChatRoom
from django.core.cache import cache
from channels import Group
from channels.auth import channel_session_user_from_http, channel_session_user
from django.utils import timezone

GLOBAL_CHAT = 'chat'
GLOBAL_CHAT_MEMBERS = 'chat_members'

log = logging.getLogger(__name__)


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

    # send updated member list
    members = cache.get(GLOBAL_CHAT_MEMBERS, defaultdict(int))
    members[message.user] += 1  # connections number (user can open many tabs)
    cache.set(GLOBAL_CHAT_MEMBERS, members, None)

    Group(GLOBAL_CHAT).send({
        'text': json.dumps({
            'chat_members': [user.username for user in members.keys()]
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
    if members[message.user] == 1:
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


# Connected to websocket.receive
@channel_session_user
def ws_message(message):
    if not message.user.is_active:
        return

    try:
        data = json.loads(message['text'])
    except ValueError:
        log.debug("ws message isn't json text: %s", message['text'])
        return

    if 'text' not in data:
        log.debug("ws message unexpected format: %s", data)
        return

    chat_message(GLOBAL_CHAT, {
        'text': data['text'],
        'sender': message.user.username
    })


# Connected to websocket.disconnect
@channel_session_user
def ws_disconnect(message):
    Group(GLOBAL_CHAT).discard(message.reply_channel)

    # check the number of clients this user still has
    # and if zero, then remove him from members list
    members = cache.get(GLOBAL_CHAT_MEMBERS, defaultdict(int))
    members[message.user] -= 1
    if members[message.user] <= 0:  # no connections left
        del members[message.user]

        # notify other members about user disconnect
        chat_message(GLOBAL_CHAT, {
            'text': 'User %s disconnected from the game.' % message.user.username,
            'sender': 'System',
        })

        # send updated members list
        Group(GLOBAL_CHAT).send({
            'text': json.dumps({
                'chat_members': [user.username for user in members.keys()]
            })
        })
    cache.set(GLOBAL_CHAT_MEMBERS, members, None)
