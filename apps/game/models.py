from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# This can be global chat, game chat, game police chat, etc
class ChatRoom(models.Model):
    name = models.TextField(unique=True)


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, related_name='messages')
    sender = models.TextField()  # TODO: replace with User?
    text = models.TextField()
    highlight = models.TextField()  # recipient's nick
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)


class Game(models.Model):
    name = models.TextField()
    players_num = models.PositiveSmallIntegerField()
    level = models.PositiveSmallIntegerField(default=1)
    type = models.TextField(default='Normal')  # Normal, Personal, etc
    players = models.ManyToManyField(User)
    chat = models.OneToOneField(ChatRoom, null=True)
    winner = models.TextField()  # TODO: create Role model?

    status = models.TextField(default='Created')  # Started, Finished, Canceled, etc
    created_by = models.TextField()  # TODO: replace with User?
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

