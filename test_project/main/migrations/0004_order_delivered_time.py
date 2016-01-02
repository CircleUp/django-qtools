# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_auto_20151227_1508'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivered_time',
            field=models.DateTimeField(null=True),
        ),
    ]
