# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0004_order_delivered_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='miscmodel',
            name='main_info',
            field=models.OneToOneField(related_name='extra_info', null=True, to='main.MiscModel'),
        ),
    ]
