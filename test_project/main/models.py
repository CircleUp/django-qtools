from datetime import timedelta

from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone
from qtools import q_method, nested_q
from qtools.filterq import obj_matches_q


class OrderQuerySet(QuerySet):
    @q_method
    def is_delivered(cls):
        return Q(delivered_time__isnull=False)

    @q_method
    def delivered_in_last_x_days(cls, days):
        return Q(delivered_time__gt=timezone.now() - timedelta(days=days))

    @q_method
    def cost_between(cls, lower=0, upper=100000):
        return Q(price__gte=lower, price__lte=upper)


class Order(models.Model):
    name_on_order = models.CharField(max_length=75)
    price = models.DecimalField(decimal_places=4, max_digits=10)
    delivered_time = models.DateTimeField(null=True)

    objects = OrderQuerySet.as_manager()


class Topping(models.Model):
    name = models.CharField(max_length=50)
    is_gluten_free = models.BooleanField(True)


class PizzaQuerySet(QuerySet):
    @q_method
    def is_delivered(cls):
        return nested_q('order', OrderQuerySet.is_delivered())

    @q_method
    def delivered_in_last_x_days(cls, days):
        return nested_q('order', OrderQuerySet.delivered_in_last_x_days(days))

    @q_method
    def is_delivered_using_cls(cls):
        return cls.is_delivered()

    def is_delivered_using_self(self):
        return self.filter(self.is_delivered.q())

class Pizza(models.Model):
    created = models.DateTimeField()
    order = models.ForeignKey(Order, null=True)
    diameter = models.FloatField()
    toppings = models.ManyToManyField(Topping)

    objects = PizzaQuerySet.as_manager()

    is_delivered = PizzaQuerySet.is_delivered.as_property(execute_in_memory=True)
    is_delivered_method = PizzaQuerySet.is_delivered.as_method(execute_in_memory=True)


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
    main_info = models.OneToOneField('self', related_name='extra_info', null=True)

    def __repr__(self):
        return '<MiscModel: %s>' % str(self.pk)
