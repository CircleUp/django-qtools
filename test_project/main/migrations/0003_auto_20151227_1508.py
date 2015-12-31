# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20151226_2023'),
    ]

    operations = [
        migrations.AlterField(
            model_name='miscmodel',
            name='text',
            field=models.CharField(max_length=10, null=True),
        ),
    ]
