import datetime

from django.db import connection, models
from django.db.backends.utils import typecast_timestamp as django_typecast_timestamp
from django.db.models.fields.related import ForeignObjectRel
from django.utils import six

RELATED_FIELD_CLASSES = [ForeignObjectRel]
try:
    # django 1.6
    from django.db.models.related import RelatedObject
    RELATED_FIELD_CLASSES.append(RelatedObject)
except ImportError:
    pass

RELATED_FIELD_CLASSES = tuple(RELATED_FIELD_CLASSES)

from .exceptions import InvalidFieldLookupCombo


def limit_float_to_digits(num, digits):
    text = repr(num)
    digits_only = text.replace('-', '').replace('.', '').lstrip('0-.')
    digits_to_remove = max(len(digits_only) - digits, 0)
    if digits_to_remove > 0:
        return float(text[:-digits_to_remove])
    return num


def django_instances_to_keys(*objs):
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


def assert_is_valid_lookup_for_field(lookup, simple_type):
    valid_types = VALID_FIELD_LOOKUPS.get(simple_type, [])
    if lookup not in valid_types:
        raise InvalidFieldLookupCombo('Using the %s lookup on a %s field is not supported.' % (lookup, simple_type))


def django_instances_to_keys_for_comparison(fn):
    def wrap_fn(cls, a, b, simple_field_type=None):
        a, b = django_instances_to_keys(a, b)
        if a is None or b is None:
            return False
        return fn(cls, a, b, simple_field_type)

    return wrap_fn


def typecast_timestamp(obj_value):
    if not isinstance(obj_value, (datetime.datetime, datetime.date)):
        try:
            obj_value = django_typecast_timestamp(obj_value)
        except (ValueError, TypeError):
            obj_value = None
    return obj_value


def date_lookup(fn):
    def wrapper(cls, obj_value, query_value, simple_field_type):
        query_value = int(query_value)
        obj_value = typecast_timestamp(obj_value)

        if obj_value is None:
            return False

        result = fn(cls, obj_value, query_value, simple_field_type)

        return result

    return wrapper


def to_str(text):
    if not isinstance(text, six.string_types):
        text = str(text)
    return text


def remove_trailing_spaces_if_string(val):
    if isinstance(val, six.string_types):
        return val.rstrip(' ')
    return val


_DB_TYPES_SIMPLE_MAP = {
    'bool':             'boolean',
    'integer':          'number',
    'float':            'number',
    'double precision': 'number',
    'real':             'number',
    'decimal':          'number',
    'text':             'string',
    'datetime':         'datetime',
    'date':             'date'
}


def get_field_simple_datatype(field):
    if isinstance(field, RELATED_FIELD_CLASSES):
        return 'number'

    db_field_type = field.db_type(connection)

    if 'varchar' in db_field_type:
        return 'string'

    if 'numeric' in db_field_type:
        return 'number'
    
    if 'datetime' in db_field_type:
        return 'datetime'

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
    elif isinstance(q_obj, tuple):
        key, value = q_obj
        return prefix + '__' + key, value
    raise Exception("Not a Q object")
