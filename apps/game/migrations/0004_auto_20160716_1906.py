# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-07-16 16:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0003_game'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='chat',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='game.ChatRoom'),
        ),
        migrations.AlterField(
            model_name='game',
            name='timestamp',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='game',
            name='type',
            field=models.TextField(default='Normal'),
        ),
    ]
