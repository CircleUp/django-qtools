from functools import partial

from django.db.models import Q


class ThrowExceptionIfUsed(object):
    def __getattribute__(self, item):
        raise Exception('The self parameter cannot be used in methods decorated with q_method.')


DO_NOT_USE = ThrowExceptionIfUsed()


def q_method(fn):
    """
    Decorator for queryset methods that return Q objects.

    Any methods decorated with this must return a Q object.

    The 'self' argument is actually an unusable object but is left there so code checkers don't complain.

    The original function that returns Q objects can be accessed like this:

        class CustomQuerySet(QuerySet):

            @q_method
            def custom_method(self, limit):
                return Q(price__gt=a)

        # accessing the q method directly
        CustomQuerySet.custom_method.q(limit=5)
    """
    q_func = partial(fn, DO_NOT_USE)

    def qs_func(self, *args, **kwargs):
        q = q_func(*args, **kwargs)
        if not isinstance(q, Q):
            raise ValueError('QuerySet methods decorated with q_method must return a Q object.')
        return self.filter(q)

    qs_func.q = q_func
    return qs_func
