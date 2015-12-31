# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MiscModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('nullable_boolean', models.NullBooleanField()),
                ('boolean', models.BooleanField()),
                ('integer', models.IntegerField(null=True)),
                ('float', models.FloatField(null=True)),
                ('decimal', models.DecimalField(null=True, max_digits=10, decimal_places=4)),
                ('text', models.CharField(max_length=75, null=True)),
                ('date', models.DateField(null=True)),
                ('datetime', models.DateTimeField(null=True)),
                ('foreign', models.ForeignKey(to='main.MiscModel')),
                ('many', models.ManyToManyField(related_name='many_rel_+', to='main.MiscModel')),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name_on_order', models.CharField(max_length=75)),
                ('price', models.DecimalField(max_digits=10, decimal_places=4)),
            ],
        ),
        migrations.CreateModel(
            name='Pizza',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField()),
                ('diameter', models.FloatField()),
                ('order', models.ForeignKey(to='main.Order')),
            ],
        ),
        migrations.CreateModel(
            name='Topping',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('is_gluten_free', models.BooleanField(verbose_name=True)),
            ],
        ),
        migrations.AddField(
            model_name='pizza',
            name='toppings',
            field=models.ManyToManyField(to='main.Topping'),
        ),
    ]
