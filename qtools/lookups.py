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
import operator
import re
from functools import partial

from .exceptions import InvalidLookupValue
from .utils import django_instances_to_keys_for_comparison, date_lookup, to_str


def exact(a, b):
    return a is not None and a == b


def iexact(a, b):
    if a is None:
        return False

    return to_str(a).lower() == to_str(b).lower()


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
        raise InvalidLookupValue('Must use a string or compiled pattern with the regex lookup.')

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
        raise InvalidLookupValue('Range lookup must receive a (min, max) tuple.')

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


def isnull(val, is_null):
    return (val is None) == bool(is_null)


LOOKUPS = {
    'exact':       exact,
    'iexact':      iexact,
    'contains':    contains,
    'icontains':   icontains,
    'in':          in_func,
    'gt':          django_instances_to_keys_for_comparison(operator.gt),
    'gte':         django_instances_to_keys_for_comparison(lambda a, b: a >= b),
    'lt':          django_instances_to_keys_for_comparison(operator.lt),
    'lte':         django_instances_to_keys_for_comparison(lambda a, b: a <= b),
    'startswith':  startswith,
    'istartswith': istartswith,
    'endswith':    endswith,
    'iendswith':   iendswith,
    'range':       range_func,
    'year':        year,
    'month':       date_lookup(lambda dt, month: dt.month == month),
    'day':         date_lookup(lambda dt, day: dt.day == day),
    # week day stuff
    # https://code.djangoproject.com/ticket/10345
    # https://code.djangoproject.com/ticket/7672#comment:3
    'week_day':    date_lookup(lambda dt, week_day: dt.date().isoweekday() + 1 == week_day),
    'hour':        date_lookup(lambda dt, hour: dt.hour == hour),
    'minute':      date_lookup(lambda dt, minute: dt.minute == minute),
    'second':      date_lookup(lambda dt, second: dt.second == second),
    'isnull':      isnull,
    'search':      contains,
    'regex':       regex,
    'iregex':      iregex,
}

SUPPORTED_LOOKUP_NAMES = LOOKUPS.keys()


def evaluate_lookup(lookup, obj_value, query_value):
    return LOOKUPS[lookup](obj_value, query_value)
