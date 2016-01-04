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
import re

from django.conf import settings

from utils import django_instances_to_keys_for_comparison, date_lookup
from .exceptions import InvalidLookupValue
from .utils import to_str


class PythonLookups(object):
    SUPPORTED_LOOKUP_NAMES = [
        'gt', 'in', 'month', 'isnull', 'endswith', 'week_day', 'year', 'regex', 'gte',
        'contains', 'lt', 'startswith', 'iendswith', 'icontains', 'iexact', 'exact',
        'day', 'minute', 'search', 'hour', 'iregex', 'second', 'range', 'istartswith', 'lte'
    ]

    LOOKUP_FUNC_OVERRIDES = {
        'in':    'in_func',
        'range': 'range_func',
        'search': 'contains'
    }

    @classmethod
    def exact(cls, a, b):
        return a is not None and a == b

    @classmethod
    def iexact(cls, a, b):
        if a is None:
            return False

        return to_str(a).lower() == to_str(b).lower()

    @classmethod
    def contains(cls, haystack, needle):
        if haystack is None:
            return False

        try:
            iter(haystack)
        except TypeError:
            haystack = to_str(haystack)

        if isinstance(haystack, basestring):
            needle = to_str(needle)

        return needle in haystack

    @classmethod
    def icontains(cls, haystack, needle):
        if haystack is None:
            return False

        haystack = to_str(haystack)
        needle = to_str(needle)

        return needle.lower() in haystack.lower()

    @classmethod
    def in_func(cls, needle, haystack):
        if needle is None:
            # mirrors how sql treats null values
            return False

        if isinstance(haystack, basestring):
            needle = str(needle)

        return needle in haystack

    @classmethod
    @django_instances_to_keys_for_comparison
    def gt(cls, a, b):
        return a > b

    @classmethod
    @django_instances_to_keys_for_comparison
    def gte(cls, a, b):
        return a >= b

    @classmethod
    @django_instances_to_keys_for_comparison
    def lt(cls, a, b):
        return a < b

    @classmethod
    @django_instances_to_keys_for_comparison
    def lte(cls, a, b):
        return a <= b

    @classmethod
    def range_func(cls, value, rng):
        if len(rng) != 2:
            raise InvalidLookupValue('Range lookup must receive a (min, max) tuple.')

        if value is None:
            return False

        lower, upper = rng
        if lower is None or upper is None:
            return False

        return rng[0] <= value <= rng[1]

    @classmethod
    def endswith(cls, text, ending):
        if text is None:
            return False

        text = to_str(text)
        ending = to_str(ending)
        return text.endswith(ending)

    @classmethod
    def iendswith(cls, text, ending):
        if text is None:
            return False

        text = to_str(text).lower()
        ending = to_str(ending).lower()
        return text.endswith(ending)

    @classmethod
    def startswith(cls, text, beginning):
        if text is None:
            return False

        text = to_str(text)
        beginning = to_str(beginning)
        return text.startswith(beginning)

    @classmethod
    def istartswith(cls, text, beginning):
        if text is None:
            return False

        text = to_str(text).lower()
        beginning = to_str(beginning).lower()
        return text.startswith(beginning)

    @classmethod
    @date_lookup
    def year(cls, dt, yr):
        yr = int(yr)

        datetime.date(yr, 1, 1)  # throws exception for invalid years
        return dt.year == yr

    @classmethod
    @date_lookup
    def month(cls, dt, month):
        return dt.month == month

    @classmethod
    @date_lookup
    def day(cls, dt, day):
        return dt.day == day

    @classmethod
    @date_lookup
    def week_day(cls, dt, week_day):
        # https://code.djangoproject.com/ticket/10345
        # https://code.djangoproject.com/ticket/7672#comment:3
        return dt.date().isoweekday() + 1 == week_day

    @classmethod
    @date_lookup
    def hour(cls, dt, hour):
        return dt.hour == hour

    @classmethod
    @date_lookup
    def minute(cls, dt, minute):
        return dt.minute == minute

    @classmethod
    @date_lookup
    def second(cls, dt, second):
        return dt.second == second

    @classmethod
    def isnull(cls, val, is_null):
        return (val is None) == bool(is_null)

    @classmethod
    def get_lookup_function(cls, lookup_name):
        lookup_func_name = cls.LOOKUP_FUNC_OVERRIDES.get(lookup_name, lookup_name)
        return getattr(cls, lookup_func_name)

    @classmethod
    def evaluate_lookup(cls, lookup_name, obj_value, query_value):
        lookup_func = cls.get_lookup_function(lookup_name)
        return lookup_func(obj_value, query_value)

    @classmethod
    def regex(cls, text, pattern, flags=0):
        REGEX_TYPE = type(re.compile(''))
        if not isinstance(pattern, (REGEX_TYPE, basestring)):
            raise InvalidLookupValue('Must use a string or compiled pattern with the regex lookup.')

        if text is None:
            return False

        text = to_str(text)

        return (re.search(pattern, text, flags=flags) is not None)

    @classmethod
    def iregex(cls, text, pattern):
        return cls.regex(text, pattern, flags=re.IGNORECASE)


class SqLiteCompatibleLookups(PythonLookups):
    pass


class MySqlCompatibleLookups(PythonLookups):
    pass


ENGINE_ADAPTER_MAPPING = {
    'django.db.backends.mysql':   MySqlCompatibleLookups,
    'django.db.backends.sqlite3': SqLiteCompatibleLookups,
    'python':                     PythonLookups,
    'mysql':                      MySqlCompatibleLookups,
    'sqlite':                     SqLiteCompatibleLookups
}


def get_lookup_adapter(db_engine=None):
    if not db_engine:
        db_engine = settings.DATABASES['default']['ENGINE']

    return ENGINE_ADAPTER_MAPPING.get(db_engine, PythonLookups)
