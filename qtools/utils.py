import datetime

from django.db import connection, models
from django.db.backends.utils import typecast_timestamp

from .exceptions import InvalidLookupUsage


def _django_instances_to_keys(*objs):
    return_objs = []
    for obj in objs:
        if isinstance(obj, models.Model):
            obj = obj.pk
        return_objs.append(obj)
    return return_objs


def assert_is_valid_lookup_for_field(lookup, field):
    from .lookups import VALID_FIELD_LOOKUPS
    from .pyq import simplify_data_types

    simple_type = simplify_data_types(field.db_type(connection))

    if simple_type in VALID_FIELD_LOOKUPS:

        if lookup not in VALID_FIELD_LOOKUPS[simple_type]:
            raise InvalidLookupUsage('Using the %s lookup on a %s field is not supported.' % (lookup, simple_type))


def django_instances_to_keys_for_comparison(fn):
    def wrap_fn(a, b):
        a, b = _django_instances_to_keys(a, b)
        if a is None or b is None:
            return False
        return fn(a, b)

    return wrap_fn


def date_lookup(fn):
    def wrapper(obj_value, query_value):
        query_value = int(query_value)
        if not isinstance(obj_value, (datetime.datetime, datetime.date)):
            try:
                obj_value = typecast_timestamp(obj_value)
            except (ValueError, TypeError):
                obj_value = None
        if obj_value is None:
            return False

        return fn(obj_value, query_value)

    return wrapper


def to_str(text):
    if not isinstance(text, basestring):
        text = str(text)
    return text
