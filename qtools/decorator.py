from functools import partial
from types import MethodType

from django.db import models

from .utils import nested_q

LOOKUP_NAME = '__qmatches'

class ThrowExceptionIfUsed(object):
    def __getattribute__(self, item):
        raise Exception('The self parameter cannot be used in methods decorated with q_method.')

class QMethod(object):
    """
    Decorator that converts methods that return Q objects into queryset methods
    """

    def __init__(self, q_method_obj=None):
        self.q_method = q_method_obj
        self.__doc__ = q_method_obj.__doc__
        self.q = partial(q_method_obj, ThrowExceptionIfUsed())

    def __get__(self, obj, parent_class=None):
        if obj is None:
            # accessed from class
            return self

        if issubclass(parent_class, models.QuerySet):
            # decorator used on queryset method

            def qs_func(*args, **kwargs):
                return obj.filter(self.q(*args, **kwargs))
            qs_func.q = self.q
            return qs_func
        else:
            raise Exception('the @q_method decorator should only be used on QuerySets')


q_method = QMethod


def manager__getattr__(self, name):
    if name.startswith('_'):
        raise AttributeError()

    qs_method = getattr(self.get_queryset(), name)

    # noinspection PyUnusedLocal
    def manager_method(mgr_self, *args, **kwargs):
        return qs_method(*args, **kwargs)

    manager_method.__name__ = qs_method.__name__
    manager_method.__doc__ = qs_method.__doc__
    manager_method.q = qs_method.q

    setattr(self, name, MethodType(manager_method, self, type(self)))
    return getattr(self, name)


class QMethodQuerySet(models.QuerySet):

    @classmethod
    def get_manager_class(cls):
        # Address the circular dependency between `Queryset` and `Manager`.
        from django.db.models.manager import Manager
        manager_cls = Manager.from_queryset(cls)
        setattr(manager_cls, '__getattr__', MethodType(manager__getattr__, None, manager_cls))
        return manager_cls

    # noinspection PyMethodParameters
    def as_manager(cls):
        """
        Override the manager generation.

        if we don't patch the as_manager as well then these methods will not work on the first call to
        objects.  For example User.objects.all().my_dual_property() will work but
        User.objects.my_dual_property() will not
        """

        # Address the circular dependency between `Queryset` and `Manager`.
        from django.db.models.manager import Manager
        manager_cls = Manager.from_queryset(cls)
        # the q_method decorated methods are classes so Django does not copy them over, as such
        # trying to access them will hit __getattr__, which will then create and attach the manager
        # method version
        setattr(manager_cls, '__getattr__', MethodType(manager__getattr__, None, manager_cls))

        manager = manager_cls()
        manager._built_with_as_manager = True
        return manager

    as_manager.queryset_only = True
    as_manager = classmethod(as_manager)

    def _filter_or_exclude(self, negate, *args, **kwargs):
        """Allow use of the custom lookup"""
        args = list(args)
        new_kwargs = {}
        # look for our special lookup name
        for key, value in kwargs.items():
            if key.endswith(LOOKUP_NAME):
                if isinstance(value, models.Q):
                    args.append(nested_q(key.replace(LOOKUP_NAME, ''), value))
                else:
                    raise TypeError('%s lookup requires Q objects, not %s' % (LOOKUP_NAME, str(type(value))))
            else:
                new_kwargs[key] = value

        return super(QMethodQuerySet, self)._filter_or_exclude(negate, *args, **new_kwargs)
