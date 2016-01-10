"""
Python equivalents to Django lookups

These are made to mimic how a SQL query would respond. Some things to note:
 - in SQL any comparison to a null value will return false (except IS NULL). These lookups treat
   `None` the same way.
 - SQL is more forgiving than it should be. While SQL may allow you to use a date function on a
   boolean value, this library will throw an exception. Consult VALID_FIELD_LOOKUPS to see what
   is supported.
 - This was extensively tested against sqlite and may reflect some idiosyncrasies of sqlite until
   we do further testing.
"""
import datetime
import logging
import re
from decimal import Decimal

from django.conf import settings
from django.utils import six

from .exceptions import InvalidLookupValue, InvalidLookupUsage
from .utils import to_str, typecast_timestamp, django_instances_to_keys_for_comparison, date_lookup, limit_float_to_digits, remove_trailing_spaces_if_string

logger = logging.getLogger(__name__)


class PythonLookups(object):
    SUPPORTED_LOOKUP_NAMES = [
        'gt', 'in', 'month', 'isnull', 'endswith', 'week_day', 'year', 'regex', 'gte',
        'contains', 'lt', 'startswith', 'iendswith', 'icontains', 'iexact', 'exact',
        'day', 'minute', 'search', 'hour', 'iregex', 'second', 'range', 'istartswith', 'lte'
    ]

    LOOKUP_FUNC_OVERRIDES = {
        'in':     'in_func',
        'range':  'range_func',
        'search': 'contains'
    }

    @classmethod
    def exact(cls, a, b, simple_field_type=None):
        return a is not None and a == b

    @classmethod
    def iexact(cls, a, b, simple_field_type=None):
        if a is None:
            return False
        return to_str(a).lower() == to_str(b).lower()

    @classmethod
    def contains(cls, haystack, needle, simple_field_type=None):
        if haystack is None:
            return False

        try:
            iter(haystack)
        except TypeError:
            haystack = to_str(haystack)

        if isinstance(haystack, six.string_types):
            needle = to_str(needle)

        return needle in haystack

    @classmethod
    def icontains(cls, haystack, needle, simple_field_type=None):
        if haystack is None:
            return False

        haystack = to_str(haystack)
        needle = to_str(needle)

        return needle.lower() in haystack.lower()

    @classmethod
    def in_func(cls, needle, haystack, simple_field_type=None):
        if needle is None:
            # mirrors how sql treats null values
            return False

        if simple_field_type == 'boolean':
            haystack = [bool(v) for v in haystack]
        elif simple_field_type == 'number':
            haystack = [Decimal(v) for v in haystack]
        elif simple_field_type == 'string':
            haystack = [to_str(v) for v in haystack]
        else:
            haystack = [v for v in haystack]

        if isinstance(haystack, six.string_types):
            needle = to_str(needle)

        return needle in haystack

    @classmethod
    @django_instances_to_keys_for_comparison
    def gt(cls, a, b, simple_field_type=None):
        return a > b

    @classmethod
    @django_instances_to_keys_for_comparison
    def gte(cls, a, b, simple_field_type=None):
        return a >= b

    @classmethod
    @django_instances_to_keys_for_comparison
    def lt(cls, a, b, simple_field_type=None):
        return a < b

    @classmethod
    @django_instances_to_keys_for_comparison
    def lte(cls, a, b, simple_field_type=None):
        return a <= b

    @classmethod
    def range_func(cls, value, rng, simple_field_type=None):
        if len(rng) != 2:
            raise InvalidLookupValue('Range lookup must receive a (min, max) tuple.')

        if value is None:
            return False

        lower, upper = rng
        if lower is None or upper is None:
            return False

        return rng[0] <= value <= rng[1]

    @classmethod
    def endswith(cls, text, ending, simple_field_type=None):
        if text is None:
            return False

        text = to_str(text)
        ending = to_str(ending)
        return text.endswith(ending)

    @classmethod
    def iendswith(cls, text, ending, simple_field_type=None):
        if text is None:
            return False

        text = to_str(text).lower()
        ending = to_str(ending).lower()
        return text.endswith(ending)

    @classmethod
    def startswith(cls, text, beginning, simple_field_type=None):
        if text is None:
            return False

        text = to_str(text)
        beginning = to_str(beginning)
        return text.startswith(beginning)

    @classmethod
    def istartswith(cls, text, beginning, simple_field_type=None):
        if text is None:
            return False

        text = to_str(text).lower()
        beginning = to_str(beginning).lower()
        return text.startswith(beginning)

    @classmethod
    def year(cls, dt, yr, simple_field_type=None):
        dt = typecast_timestamp(dt)
        yr = int(yr)

        datetime.date(yr, 1, 1)  # throws exception for invalid years

        if dt is None:
            return False

        return dt.year == yr

    @classmethod
    @date_lookup
    def month(cls, dt, month, simple_field_type=None):
        return dt.month == month

    @classmethod
    @date_lookup
    def day(cls, dt, day, simple_field_type=None):
        return dt.day == day

    @classmethod
    @date_lookup
    def week_day(cls, dt, week_day, simple_field_type=None):
        # https://code.djangoproject.com/ticket/10345
        # https://code.djangoproject.com/ticket/7672#comment:3
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        obj_weekday = (dt.isoweekday() + 1) % 7 or 7
        return obj_weekday == week_day

    @classmethod
    @date_lookup
    def hour(cls, dt, hour, simple_field_type=None):
        return dt.hour == hour

    @classmethod
    @date_lookup
    def minute(cls, dt, minute, simple_field_type=None):
        return dt.minute == minute

    @classmethod
    @date_lookup
    def second(cls, dt, second, simple_field_type=None):
        return dt.second == second

    @classmethod
    def isnull(cls, val, is_null, simple_field_type=None):
        return (val is None) == bool(is_null)

    @classmethod
    def regex(cls, text, pattern, simple_field_type=None, flags=0):
        REGEX_TYPE = type(re.compile(''))
        if not isinstance(pattern, (REGEX_TYPE, six.string_types)):
            raise InvalidLookupValue('Must use a string or compiled pattern with the regex lookup. Received: %s' % repr(pattern))

        if text is None:
            return False

        text = to_str(text)

        return re.search(pattern, text, flags=flags) is not None

    @classmethod
    def iregex(cls, text, pattern, simple_field_type=None):
        return cls.regex(text, pattern, flags=re.IGNORECASE)

    @classmethod
    def get_lookup_function(cls, lookup_name):
        lookup_func_name = cls.LOOKUP_FUNC_OVERRIDES.get(lookup_name, lookup_name)
        return getattr(cls, lookup_func_name)

    @classmethod
    def prep_values(cls, lookup_name, obj_value, query_value, simple_field_type):
        return obj_value, query_value

    @classmethod
    def evaluate_lookup(cls, lookup_name, obj_value, query_value, simple_field_type=None):
        obj_value, query_value = cls.prep_values(lookup_name, obj_value, query_value, simple_field_type)
        lookup_func = cls.get_lookup_function(lookup_name)
        return lookup_func(obj_value, query_value, simple_field_type=simple_field_type)


class SqLiteCompatibleLookups(PythonLookups):
    pass


class MySqlCompatibleLookups(PythonLookups):

    LOOKUP_FUNC_OVERRIDES = {
        'in':     'in_func',
        'range':  'range_func',
        'search': 'contains',
    }

    @classmethod
    def in_func(cls, needle, haystack, simple_field_type=None):
        if isinstance(needle, six.string_types):
            needle = needle.lower()

        if isinstance(haystack, six.string_types):
            haystack = haystack.lower()

        if simple_field_type == 'boolean':
            haystack = [bool(v) for v in haystack]
        elif simple_field_type == 'number':
            haystack = [Decimal(v) for v in haystack]
        elif simple_field_type == 'string':
            haystack = [to_str(v).lower() for v in haystack]
        else:
            haystack = [v for v in haystack]

        needle = remove_trailing_spaces_if_string(needle)
        haystack = remove_trailing_spaces_if_string(haystack)

        if isinstance(haystack, list):
            haystack = [remove_trailing_spaces_if_string(v) for v in haystack]

        return super(MySqlCompatibleLookups, cls).in_func(needle, haystack, simple_field_type)

    @classmethod
    def regex(cls, text, pattern, simple_field_type=None, flags=0):
        if pattern == '':
            raise ValueError('MySQL regex cannot accept an empty string as a valid regex.')
        return super(MySqlCompatibleLookups, cls).regex(text, pattern, simple_field_type=simple_field_type, flags=flags)

    @classmethod
    def year(cls, dt, yr, simple_field_type=None):
        yr = int(yr)
        datetime.date(yr, 1, 1)
        if simple_field_type == 'datetime':
            if yr < 1900:
                raise ValueError('adapt_datetime_with_timezone_support throws an error when trying to query for a year < 1900 so qtools does not support this in MySql mode')
        return super(MySqlCompatibleLookups, cls).year(dt, yr, simple_field_type)

    @classmethod
    def exact(cls, obj_value, query_value, simple_field_type=None):
        if simple_field_type == 'string':
            if query_value is not None:
                query_value = to_str(query_value).lower()
            if obj_value is not None:
                obj_value = to_str(obj_value).lower()

        obj_value = remove_trailing_spaces_if_string(obj_value)
        query_value = remove_trailing_spaces_if_string(query_value)
        return super(MySqlCompatibleLookups, cls).exact(obj_value, query_value, simple_field_type)

    @classmethod
    def prep_values(cls, lookup_name, obj_value, query_value, simple_field_type):

        # mysql only returned values with 15 digits so we truncate our python floats to the same length
        if isinstance(obj_value, float):
            obj_value = limit_float_to_digits(obj_value, 15)

        if isinstance(query_value, float):
            query_value = limit_float_to_digits(query_value, 15)

        if isinstance(query_value, datetime.datetime):
            query_value = query_value.replace(microsecond=0)

        if lookup_name in ['gt', 'gte', 'lt', 'lte']:
            if simple_field_type == 'string':
                raise InvalidLookupUsage('Comparing strings in python can have different results than you would get in MySql due to python not being aware of the collation.')

            if isinstance(obj_value, six.string_types):
                # when doing string comparisons mysql is not case sensitive in the most commonly used collations
                obj_value = obj_value.lower()

            obj_value = remove_trailing_spaces_if_string(obj_value)
            query_value = remove_trailing_spaces_if_string(query_value)

        return obj_value, query_value

    @classmethod
    def evaluate_lookup(cls, lookup_name, obj_value, query_value, simple_field_type=None):
        if lookup_name in ['gt', 'gte', 'lt', 'lte']:
            if query_value is None:
                return False
        return super(MySqlCompatibleLookups, cls).evaluate_lookup(lookup_name, obj_value, query_value, simple_field_type)


ENGINE_ADAPTER_MAPPING = {
    'django.db.backends.mysql':   MySqlCompatibleLookups,
    'django.db.backends.sqlite3': SqLiteCompatibleLookups,
    'python':                     PythonLookups,
    'mysql':                      MySqlCompatibleLookups,
    'sqlite':                     SqLiteCompatibleLookups
}


def get_lookup_adapter(db_engine=None):
    if not db_engine or not isinstance(db_engine, six.string_types):
        db_engine = settings.DATABASES['default']['ENGINE']

    return ENGINE_ADAPTER_MAPPING.get(db_engine, PythonLookups)
