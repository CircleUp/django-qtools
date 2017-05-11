# Q Tools: A Better Way to Write Django Queries

**Write DRY, composable filtering logic for data queries and instance methods.**

[ ![Codeship Status for CircleUp/django-qtools](https://app.codeship.com/projects/9cffff70-996d-0133-b554-2e043ba8a616/status?branch=master)](https://app.codeship.com/projects/126259)


Standard Django forces business logic to be repeated as it's used in different contexts (querying, instance methods, querying related objects).  This repetition makes it hard to maintain and definitions frequently become out of sync.  This library allows a piece of filtering logic to be written once and then used in many different contexts.

## Features
 - Keep code DRY. Write filter logic once, use many places.
 - Prevent repeated definitions from getting out of sync
 - More maintainable code. Just change the one definition.
 - Reduce db queries by filtering in-memory.
 - Supports all Django 1.8 lookups (exact, in, contains, etc.)
 - Switch into different compatibility modes depending on db (mysql, sqlite, etc)
 - Tested in Python 2.7, 3.5 and Django 1.7 and 1.8

## Example
```python
from django.db import models

class OrderQuerySet(QuerySet):
    @q_method
    def is_delivered(self):
        return Q(delivered_time__isnull=False)

class Order(models.Model):
    name_on_order = models.CharField(max_length=75)
    price = models.DecimalField(decimal_places=4, max_digits=10)
    delivered_time = models.DateTimeField(null=True)

    objects = OrderQuerySet.as_manager()

class PizzaQuerySet(QuerySet):
    @q_method
    def is_delivered(self):
        return nested_q('order', OrderQuerySet.is_delivered.q())


class Pizza(models.Model):
    created = models.DateTimeField()
    order = models.ForeignKey(Order, null=True)
    diameter = models.FloatField()

    objects = PizzaQuerySet.as_manager()

    @property
    def is_delivered(self):
        return obj_matches_q(self, PizzaQuerySet.is_delivered.q())
    
    def delivered_in_last_x_days(self, days):
        return obj_matches_q(self, PizzaQuerySet.delivered_in_last_x_days.q(days)
```

Usage
```python
order = Order(price=100, name_on_order='Bob')
pizza = Pizza(diameter=12, order=order, created=timezone.now())

order.save()
pizza.save()

assert Pizza.objects.is_delivered().count() == 0
assert Order.objects.is_delivered().count() == 0 
assert Pizza.objects.delivered_in_last_x_days(5) == 0
assert not pizza.is_delivered


order.delivered_time = timezone.now()
order.save()

assert Pizza.objects.is_delivered().count() == 1
assert Order.objects.is_delivered().count() == 1 
assert Pizza.objects.delivered_in_last_x_days(5) == 1
assert pizza.is_delivered

```
## API

### @q_method decorator

Allows a queryset method to be defined in terms of Q objects only.

```python
from qtools import q_method

class OrderQuerySet(QuerySet):
    @q_method
    def is_delivered(self):
        return Q(delivered_time__isnull=False)
        
# QuerySets work as normal
Order.objects.is_delivered()

# but we can access the q objects for use in other locations
Pizza.objects.filter(nested_q('order', OrderQuerySet.is_delivered.q()))
```

### filter_by_q(objs, q)

Filter a collection of django instances by a Q object. Note that if the fields used in the filter haven't been prefetched then calls to the database will still occur (and probably a lot of them).

```python
from qtools import filter_by_q
 
all_orders = list(Order.objects.all())
q = Q(delivered_time__isnull=False)
delivered_orders = filter_by_q(all_orders, q)
```
### obj_matches_q(obj, q)
 
Return whether a single django object matches a Q object
```python
from qtools import obj_matches_q

order = Order(delivered_time=datetime.now())
q = Q(delivered_time__isnull=False)
assert obj_matches_q(order, q)
```

### nested_q(prefix, q)
Prepend the prefix to all arguments in the Q object.

```python
from qtools import nested_q

Q(order__price=500) == nested_q('order', Q(price=500))
```

## Django Data Query Best Practices

- Don't use custom managers, use custom querysets. They're chainable.
- There should generally be one QuerySet per model that has lots of composable methods.
- Display logic (like ordering) does not belong in the QuerySet.
- If it all possible, queryset methods should be written as `@q_method`s. This will allow the same filtering logic to be used in queries from other models as well as in-memory using `obj_matches_q`.

## Known Issues
- When a django queryset filters on a related object that has a 1 to many relationship, it may return duplicate objects. This is often remedied by calling `.distinct()` on the queryset.  `obj_matches_q` does not return duplicate objects.

## Changelog

**Version 1.0 (current) **
  - Licensed under MIT
  - Added working @ CircleUp section
  - Make package available via pip 

**Version 0.9.1 **
 - week_day lookup fixed
 - automatic pull request testing
 - python 3 support
 - django 1.8 support

**Version 0.9 **
- Features
  - Supports all Django 1.8 lookups
  - Related object traversal and filtering
  - Querysets based on Q objects (q_method decorator)
  - Switch into different compatibility modes depending on db (mysql, sqlite, postgres)
- Test Cases
  - Lookups
  - Related object traversal and filtering
  - Querysets based on Q objects (q_method decorator)
  - sqlite bulk tested
  - mysql bulk tested
- Documentation
  - Example
  - Best Practices section
  - Comparison to existing projects

### Feature Comparison

**In-Memory Filtering**

Project | Handles django objects | python/filter exclude | related objects | Q objects 
--- | --- | --- | --- | ---
[Lookupy](https://github.com/naiquevin/lookupy) | N | Y | Y | Y | custom
[django-test-db](https://github.com/mjtamlyn/django-test-db/blob/master/test_db.py) | Y | Y | partial | Y | Y
[QueryStream](https://github.com/pstiasny/querystream/blob/master/querystream.py) | Y | Y | N | Y | custom
[dj.chain](https://github.com/ambv/dj.chain/blob/master/src/dj/chain/__init__.py) | Y | N | N | N | N
[djblets](https://github.com/djblets/djblets/blob/master/djblets/db/query.py) | Y | Y | N | N | N

**Querysets with Q Objects**

Project | Q object queryset methods | methods with args | Q nesting
--- | --- | --- | ---
[django-conceptq](https://github.com/yourcelf/django-conceptq) | Y | N | Y
[esp-website: query_utils](https://github.com/learning-unlimited/ESP-Website/blob/main/esp/esp/utils/query_utils.py) | N | N | Y
[django recycle](https://github.com/flc/django-recycle/blob/master/django_recycle/utils/prefixed_q.py) | N | N | Y

### Alternative APIs
These options were considered and not used.
```python
from django.db import models
from pyq import matches_q

class PizzaQuerySet(QuerySet):

    @q_method
    def delivered(Q):
        return Q(delivered__isnull=False)

    @q_method
    def diameter_larger_than(Q, diameter):
        return Q(diamter__gte=diameter)

class Pizza(models.Model):
    created = models.DateTimeField()
    delivered = models.DateTimeField()
    diameter = models.IntegerField()

    objects = PizzaQuerySet.as_manager()

    # api options

    # most explicit method, requires import, plays nice with decorators
    def is_delivered(self):
        return matches_q(self, PizzaQuerySet.delivered.q())

    # still explicit, no import required, plays nice with decorators
    def is_delivered(self):
        return self.matches_q(PizzaQuerySet.delivered.q())

    # not very explicit, a little shorter, import required, may not play nice with decorators
    @q_method
    def is_delivered(Q):
        return PizzaQuerySet.delivered.q()

   # shortest, but least readable. any arguments you might need to pass in are hidden, only works for q methods
   is_delivered = PizzaQuerySet.delivered.py_exec

   # explicit, arguments still hidden, only works for q methods
   is_delivered = q_method_to_python_method(PizzaQuerySet.delivered)

```


### Work at CircleUp

Entrepreneurs are changing what we eat, what we wear and how we shop. We are the entrepreneurs helping those dreams come to life.

Since 2012 we've grown into the largest private equity marketplace in the world by helping people invest in innovative consumer and retail companies. Growth capital is the fuel for these emerging brands, and we're working to make fundraising as frictionless as possible using software and data.

[See Open Jobs](https://circleup.com/jobs/)
