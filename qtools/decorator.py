import types
import functools
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
    def as_method(self, execute_in_memory=False):
        return QToMethodDescriptor(self.q, is_property=False, execute_in_memory=execute_in_memory)

    def as_property(self, execute_in_memory=False):
        return QToMethodDescriptor(self.q, is_property=True, execute_in_memory=execute_in_memory)

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
