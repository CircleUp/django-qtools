import types
import functools
from functools import partial

from django.utils import six
from django.db.models import Q
from qtools.filterq import obj_matches_q


class QToMethodDescriptor(object):
    def __init__(self, _q_func, is_property=False, execute_in_memory=False):
        self._q_func = _q_func
        self._is_property = is_property
        self._execute_in_memory = execute_in_memory

    def _execute(self, model_cls, model_instance, q):
        if self._execute_in_memory:
            return obj_matches_q(model_instance, q)
        else:
            return model_cls.objects.filter(q).filter(pk=model_instance.pk).exists()

    def __get__(self, instance, owner):
        if instance:
            if self._is_property:
                q = self._q_func()
                return self._execute(owner, instance, q)
            else:
                def wrapper(*args, **kwargs):
                    q = self._q_func(*args, **kwargs)
                    return self._execute(owner, instance, q)
                return wrapper
        else:
            return self


def _create_qs_instance_method(q_func, qs):
    def qs_func(*args, **kwargs):
        q = q_func(*args, **kwargs)
        return qs.filter(q)
    qs_func.q = q_func
    return qs_func


def _create_qs_class_method(q_func, qs_class):
    # in python 2, QuerySet.as_manager uses inspect.ismethod so we must return a bound MethodType
    # while in python3, QuerySet.as_manager uses inspect.isfunction so we return a plain, unbound function
    
    if six.PY2:
        def qs_func(cls, *args, **kwargs):
            return q_func(*args, **kwargs)
    elif six.PY3:
        def qs_func(*args, **kwargs):
            return q_func(*args, **kwargs)

    qs_func.q = q_func
    qs_func.as_method = lambda **kwargs: QToMethodDescriptor(q_func, is_property=False, **kwargs)
    qs_func.as_property = lambda **kwargs: QToMethodDescriptor(q_func, is_property=True, **kwargs)
    if six.PY2:
        qs_func = types.MethodType(qs_func, qs_class, qs_class)
    return qs_func


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
        def q_func(*args, **kwargs):
            q = self.fn(owner, *args, **kwargs)
            if not isinstance(q, Q):
                raise ValueError('QuerySet methods decorated with q_method must return a Q object.')
            return q

        if instance is not None:
            return _create_qs_instance_method(q_func, instance)
        else:
            return _create_qs_class_method(q_func, owner)
