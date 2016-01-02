import datetime

from django.db import connection, models
from django.db.backends.utils import typecast_timestamp

from .exceptions import InvalidFieldLookupCombo


def _django_instances_to_keys(*objs):
    """Convert django instances to keys"""
    return_objs = []
    for obj in objs:
        if isinstance(obj, models.Model):
            obj = obj.pk
        return_objs.append(obj)
    return return_objs


VALID_FIELD_LOOKUPS = {
    'boolean':  ['exact', 'in', 'isnull'],
    'number':   ['exact', 'in', 'gt', 'gte', 'lt', 'lte', 'range', 'isnull'],
    'string':   ['exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte',
                 'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'isnull', 'search', 'regex', 'iregex'],
    'date':     ['exact', 'in', 'gt', 'gte', 'lt', 'lte', 'range', 'year', 'month', 'day', 'week_day', 'isnull'],
    'datetime': ['exact', 'in', 'gt', 'gte', 'lt', 'lte', 'range', 'year', 'month', 'day', 'week_day', 'hour', 'minute', 'second', 'isnull']
}


def assert_is_valid_lookup_for_field(lookup, field):
    simple_type = simplify_data_types(field.db_type(connection))

    if simple_type in VALID_FIELD_LOOKUPS:

        if lookup not in VALID_FIELD_LOOKUPS[simple_type]:
            raise InvalidFieldLookupCombo('Using the %s lookup on a %s field is not supported.' % (lookup, simple_type))


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


_DB_TYPES_SIMPLE_MAP = {
    'bool':     'boolean',
    'integer':  'number',
    'float':    'number',
    'real':     'number',
    'decimal':  'number',
    'text':     'string',
    'datetime': 'datetime',
    'date':     'date'
}


def simplify_data_types(db_field_type):
    if 'varchar' in db_field_type:
        return 'string'

    return _DB_TYPES_SIMPLE_MAP.get(db_field_type, db_field_type)


def nested_q(prefix, q_obj):
    """
    Prefix the kwargs in a Q object with a given prefix

    For example, these are equivalent:
        q1 = nested_q('user', Q(name='Bob'))
        q2 = Q(user__name='Bob')
        assert q1 == q2
    """
    if isinstance(q_obj, models.Q):
        q = q_obj.clone()
        q.children = [nested_q(prefix, child) for child in q.children]
        return q
    key, value = q_obj
    return prefix + '__' + key, value
