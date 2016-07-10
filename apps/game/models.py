from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# This can be global chat, game chat, game police chat, etc
class ChatRoom(models.Model):
    name = models.TextField(unique=True)


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, related_name='messages')
    sender = models.TextField()
    text = models.TextField()
    highlight = models.TextField()  # recipient's nick
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
