from functools import partial


class ThrowExceptionIfUsed(object):
    def __getattribute__(self, item):
        raise Exception('The self parameter cannot be used in methods decorated with q_method.')


DO_NOT_USE = ThrowExceptionIfUsed()


def q_method(fn):
    q_func = partial(fn, DO_NOT_USE)

    def qs_func(self, *args, **kwargs):
        return self.filter(q_func(*args, **kwargs))

    qs_func.q = q_func
    return qs_func
