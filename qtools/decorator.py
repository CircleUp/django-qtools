import types
import functools
from django.db.models import Q
from qtools.filterq import obj_matches_q


class QMethodCallable(object):
    def __init__(self, q_func):
        self.q_func = q_func
        functools.update_wrapper(self, self.q_func)

    def q(self, *args, **kwargs):
        q = self.q_func(*args, **kwargs)
        if not isinstance(q, Q):
            raise ValueError('QuerySet methods decorated with q_method must return a Q object.')
        return q


class QInstanceMethodCallable(QMethodCallable):
    def __call__(self, instance, *args, **kwargs):
        q = self.q(*args, **kwargs)
        return instance.filter(q)


class QClassMethodCallable(QMethodCallable):
     def __call__(self, cls, *args, **kwargs):
        return self.q(*args, **kwargs)


class q_method(object):
    """
        A decorator that allows you to implement custom QuerySet filters as classmethod's returning a Q object

        class MyQuerySet(QuerySet):
            def costs_more_than_q(cls, price):
                return Q(price__gt=price)

            def costs_more_than(self, price):
                return self.filter(self.costs_more_than_q(price))

        MyModel.objects.costs_more_than(price)
        MyQuerySet.costs_more_than_q(price)

        vs

        class MyQuerySet(QuerySet):
            @q_method
            def costs_more_than(cls, price):
                return Q(price__gt=price)

        MyModel.objects.costs_more_than(price)
        MyQuerySet.costs_more_than(price)

    """
    def __init__(self, fn):
        self.fn = fn

    def __get__(self, instance, owner):
        q_func = types.MethodType(self.fn, owner, owner)
        if instance is not None:
            return types.MethodType(QInstanceMethodCallable(q_func), instance, owner)
        else:
            return types.MethodType(QClassMethodCallable(q_func), owner, owner)
