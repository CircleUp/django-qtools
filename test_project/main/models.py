from django.db import models


class Order(models.Model):
    name_on_order = models.CharField(max_length=75)
    price = models.DecimalField(decimal_places = 4, max_digits = 10)


class Topping(models.Model):
    name = models.CharField(max_length=50)
    is_gluten_free = models.BooleanField(True)


class Pizza(models.Model):
    created = models.DateTimeField()
    order = models.ForeignKey(Order, null=True)
    diameter = models.FloatField()
    toppings = models.ManyToManyField(Topping)


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
