# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='miscmodel',
            name='boolean',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='miscmodel',
            name='foreign',
            field=models.ForeignKey(default=None, to='main.MiscModel', null=True),
        ),
        migrations.AlterField(
            model_name='pizza',
            name='order',
            field=models.ForeignKey(to='main.Order', null=True),
        ),
    ]
