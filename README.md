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

class Pizza(models.Model, MatchesQMixin):
    delivered = models.DateTimeField()

    def is_delivered(self):
        return self.matches_q(Q(delivered__isnull=False))

```

## How

Most db queries can be written as django `Q` objects. In principle, there is no reason that the Q objects could not be executed in python as well.  Even if we can't handle all use cases, handling most of them and clearly enumerating the limitations would still be very useful.

Details
  - This library will cause N queries if not used with prefetch related. That's okay and it's the developers responsibility to make the appropriate prefetches.
  - Handling filtering on the attributes of the base object should be straight forward enough. Its handling the related objects that'll be tricky.



## To Do

- [x] Study and evaluate Lookupy and django-test-db
- [x] Enumerate test cases
- [ ] Design API
- [ ] Write test cases
  - [x] Lookups
  - [x] Related object traversal and filtering
  - [x] QuerySets based on Q objects
  - [ ] tox.ini for multiple versions of python?
- [ ] Write code
  - [x] lookups
  - [x] related object traversal and filtering code
  - [ ] matches_q model method
  - [x] querysets based on Q objects
- [ ] Test cases pass
  - [x] Lookups
  - [x] Related object traversal and filtering
  - [ ] mysql and sqlite
  - [ ] querysets based on Q objects
- [ ] Write documentation, instructions on how to test.
  - [ ] Good/Bad Example
  - [ ] Best Practices section
  - [ ] How to Contribute section
  - [ ] CircleUp recruiting blurb
  - [ ] Mention of libraries worked on
- [ ] Open source package and make it accessible via pip

### Similar Libraries

Project | Handles django objects | python/filter exclude | related objects | Q objects
--- | --- | --- | --- | ---
[Lookupy](https://github.com/naiquevin/lookupy) | N | Y | Y | Y | custom
[django-test-db](https://github.com/mjtamlyn/django-test-db/blob/master/test_db.py) | Y | Y | partial | Y | Y
[QueryStream](https://github.com/pstiasny/querystream/blob/master/querystream.py) | Y | Y | N | Y | custom
[dj.chain](https://github.com/ambv/dj.chain/blob/master/src/dj/chain/__init__.py) | Y | N | N | N | N
[djblets](https://github.com/djblets/djblets/blob/master/djblets/db/query.py) | Y | Y | N | N | N


### Alternative APIs

```python
from django.db import models
from pyq import matches_q

class PizzaQuerySet(QMethodQuerySet):

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
