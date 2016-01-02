from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone
from qtools import QMethodQuerySet, q_method, nested_q


class OrderQuerySet(QMethodQuerySet):
    @q_method
    def is_delivered(self):
        return Q(delivered_time__isnull=False)

    @q_method
    def delivered_in_last_x_days(self, days):
        return Q(delivered_time__gt=timezone.now() - timedelta(days=days))

    @q_method
    def cost_between(self, lower=0, upper=100000):
        return Q(price__gte=lower, price__lte=upper)


class Order(models.Model):
    name_on_order = models.CharField(max_length=75)
    price = models.DecimalField(decimal_places=4, max_digits=10)
    delivered_time = models.DateTimeField(null=True)

    objects = OrderQuerySet.as_manager()


class Topping(models.Model):
    name = models.CharField(max_length=50)
    is_gluten_free = models.BooleanField(True)


class PizzaQuerySet(QMethodQuerySet):
    @q_method
    def is_delivered(self):
        return nested_q('order', OrderQuerySet.is_delivered.q())

    @q_method
    def delivered_in_last_x_days(self, days):
        return nested_q('order', OrderQuerySet.delivered_in_last_x_days.q(days))


class Pizza(models.Model):
    created = models.DateTimeField()
    order = models.ForeignKey(Order, null=True)
    diameter = models.FloatField()
    toppings = models.ManyToManyField(Topping)

    objects = PizzaQuerySet.as_manager()


class MiscModel(models.Model):
    nullable_boolean = models.NullBooleanField()
    boolean = models.BooleanField(default=False)
    integer = models.IntegerField(null=True)
    float = models.FloatField(null=True)
    decimal = models.DecimalField(null=True, decimal_places=4, max_digits=10)
    text = models.CharField(null=True, max_length=10)
    date = models.DateField(null=True)
    datetime = models.DateTimeField(null=True)
    foreign = models.ForeignKey('self', null=True, default=None)
    many = models.ManyToManyField('self')

    def __repr__(self):
        return '<MiscModel: %s>' % str(self.pk)
