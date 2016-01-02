# Q Tools: A Better Way to Write Django Queries

**Write DRY, composable filtering logic for data queries and instance methods.**

Standard Django forces business logic to be repeated as it's used in different contexts (querying, instance methods, querying related objects).  This repetition makes is hard to maintain and definitions frequently become out of sync.  This library allows a piece of filtering logic to be written once and then used in many different contexts.

## Features
 - Keep code DRY. Write filter logic once, use many places.
 - Prevent repeated definitions from getting out of sync
 - More maintainable code. Just change the one definition.
 - Reduce db queries by filtering in-memory.
 - Use in testing for faster tests

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

class Pizza(models.Model, MatchesQMixin):
    delivered = models.DateTimeField()

    def is_delivered(self):
        return self.matches_q(Q(delivered__isnull=False))

 order = Order(price=100, name_on_order='Bob')
 pizza = Pizza(diameter=12, order=order, created=timezone.now())
 
 order.save()
 pizza.save()

 self.assertEqual(0, Pizza.objects.is_delivered().count())
 self.assertEqual(0, Order.objects.is_delivered().count())
 self.assertFalse(pizza.is_delivered)

 order.delivered_time = timezone.now()
 order.save()

 self.assertEqual(1, Order.objects.is_delivered().count())
 self.assertEqual(1, Pizza.objects.is_delivered().count())
 self.assertTrue(pizza.is_delivered)

```
## API

- **@q_method decorator**

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

- **filter_by_q(objs, q)**

Filter a collection of django instances by a Q object. Note that if the fields used in the filter haven't been prefetched then calls to the database will still occur (and probably a lot of them).

```python
from qtools import filter_by_q
 
all_orders = list(Order.objects.all())
q = Q(delivered_time__isnull=False)
delivered_orders = filter_by_q(all_orders, q)
```
- **obj_matches_q(obj, q)**
 
Return whether a single django object matches a Q object
```python
from qtools import obj_matches_q

order = Order(delivered_time=datetime.now())
q = Q(delivered_time__isnull=False)
assert obj_matches_q(order, q)
```

- **nested_q(prefix, q)**
Prepend the prefix to all arguments in the Q object.

```python
from qtools import nested_q

Q(order__price=500) == nested_q('order', Q(price=500))
```

## To Do

**Version 0.9**
- [x] Study and evaluate Lookupy and django-test-db
- [x] Enumerate test cases
- [x] Design API
- [x] Write test cases
  - [x] Lookups
  - [x] Related object traversal and filtering
  - [x] QuerySets based on Q objects
- [x] Write code
  - [x] lookups
  - [x] related object traversal and filtering code
  - [x] querysets based on Q objects (q_method decorator)
- [ ] Test cases pass
  - [x] Lookups
  - [x] Related object traversal and filtering
  - [x] querysets based on Q objects (q_method decorator)
  - [ ] mysql bulk tested
- [ ] Write documentation, instructions on how to test.
  - [ ] Good/Bad Example
  - [ ] Best Practices section
  - [ ] How to Contribute section
  - [ ] CircleUp recruiting blurb
  - [ ] Mention of libraries worked on

**Version 1.0**
- [ ] More tests
- [ ] Testing across environments (django and python versions)
- [ ] Automatic testing
- [ ] Generated docs - hosted somewhere
- [ ] Open source package and make it accessible via pip
 
**Future**
- [ ] Complete in-memory QuerySet replacement
- [ ] Switch into different compatibility modes depending on db (mysql, sqlite, postgres)
- [ ] Replace db backend for faster tests

### Similar Libraries

Project | Handles django objects | python/filter exclude | related objects | Q objects
--- | --- | --- | --- | ---
[Lookupy](https://github.com/naiquevin/lookupy) | N | Y | Y | Y | custom
[django-test-db](https://github.com/mjtamlyn/django-test-db/blob/master/test_db.py) | Y | Y | partial | Y | Y
[QueryStream](https://github.com/pstiasny/querystream/blob/master/querystream.py) | Y | Y | N | Y | custom
[dj.chain](https://github.com/ambv/dj.chain/blob/master/src/dj/chain/__init__.py) | Y | N | N | N | N
[djblets](https://github.com/djblets/djblets/blob/master/djblets/db/query.py) | Y | Y | N | N | N


### Alternative APIs
These options were considered.
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
