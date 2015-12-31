import re
import datetime
import operator
from functools import partial

from .exceptions import InvalidLookupUsage
from .utils import django_instances_to_keys_for_comparison, date_lookup, to_str


def contains(haystack, needle):
    if haystack is None:
        return False

    try:
        iter(haystack)
    except TypeError:
        haystack = to_str(haystack)

    if isinstance(haystack, basestring):
        needle = to_str(needle)

    return needle in haystack


def icontains(haystack, needle):
    if haystack is None:
        return False

    haystack = to_str(haystack)
    needle = to_str(needle)

    return needle.lower() in haystack.lower()


def year(dt, yr):
    datetime.date(yr, 1, 1)  # throws exception for invalid years
    return dt.year == yr


def regex(text, pattern, flags=0):
    REGEX_TYPE = type(re.compile(''))
    if not isinstance(pattern, (REGEX_TYPE, basestring)):
        raise InvalidLookupUsage('Must use a string or compiled pattern with the regex lookup.')

    if text is None:
        return False

    text = to_str(text)

    return (re.search(pattern, text, flags=flags) is not None)


iregex = partial(regex, flags=re.IGNORECASE)


def in_func(needle, haystack):
    if needle is None:
        # mirrors how sql treats null values
        return False

    if isinstance(haystack, basestring):
        needle = str(needle)

    return needle in haystack


def range_func(value, rng):
    if len(rng) != 2:
        raise InvalidLookupUsage('Range lookup must receive a (min, max) tuple.')

    if value is None:
        return False

    lower, upper = rng
    if lower is None or upper is None:
        return False

    return rng[0] <= value <= rng[1]


def endswith(text, ending):
    if text is None:
        return False

    text = to_str(text)
    ending = to_str(ending)
    return text.endswith(ending)


def iendswith(text, ending):
    if text is None:
        return False

    text = to_str(text).lower()
    ending = to_str(ending).lower()
    return text.endswith(ending)


def startswith(text, beginning):
    if text is None:
        return False

    text = to_str(text)
    beginning = to_str(beginning)
    return text.startswith(beginning)


def istartswith(text, beginning):
    if text is None:
        return False

    text = to_str(text).lower()
    beginning = to_str(beginning).lower()
    return text.startswith(beginning)


LOOKUPS = {
    'exact': lambda a, b: a is not None and a == b,
    'iexact': lambda a, b: to_str(a).lower() == to_str(b).lower(),
    'contains': contains,
    'icontains': icontains,
    'in': in_func,
    'gt': django_instances_to_keys_for_comparison(operator.gt),
    'gte': django_instances_to_keys_for_comparison(lambda a, b: a >= b),
    'lt': django_instances_to_keys_for_comparison(operator.lt),
    'lte': django_instances_to_keys_for_comparison(lambda a, b: a <= b),
    'startswith': startswith,
    'istartswith': istartswith,
    'endswith': endswith,
    'iendswith': iendswith,
    'range': range_func,
    'year': year,
    'month': date_lookup(lambda dt, month: dt.month == month),
    'day': date_lookup(lambda dt, day: dt.day == day),
    'week_day': date_lookup(lambda dt, week_day: dt.isoweekday() == week_day),
    'hour': date_lookup(lambda dt, hour: dt.hour == hour),
    'minute': date_lookup(lambda dt, minute: dt.minute == minute),
    'second': date_lookup(lambda dt, second: dt.second == second),
    'isnull': date_lookup(lambda val, isnull: (val is None) == bool(isnull)),
    'search': contains,
    'regex': regex,
    'iregex': iregex,
}

SUPPORTED_LOOKUP_NAMES = LOOKUPS.keys()

VALID_FIELD_LOOKUPS = {
    'boolean': ['exact', 'in', 'isnull'],
    'number': ['exact', 'in', 'gt', 'gte', 'lt', 'lte', 'range', 'isnull'],
    'string': ['exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'gte', 'lt', 'lte',
               'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'isnull', 'search', 'regex', 'iregex'],
    'date': ['exact', 'in', 'gt', 'gte', 'lt', 'lte', 'range', 'year', 'month', 'day', 'week_day', 'isnull'],
    'datetime': ['exact', 'in', 'gt', 'gte', 'lt', 'lte', 'range', 'year', 'month', 'day', 'week_day', 'hour', 'minute', 'second', 'isnull']
}

DATE_TRANSFORM_LOOKUPS = ['year', 'month', 'day', 'week_day', 'hour', 'minute', 'second']


def evaluate_lookup(lookup, obj_value, query_value):
    return LOOKUPS[lookup](obj_value, query_value)
