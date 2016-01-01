from django.db import models
from django.db.models.query_utils import Q

from .exceptions import NoOpFilterException
from .lookups import evaluate_lookup, SUPPORTED_LOOKUP_NAMES
from .utils import assert_is_valid_lookup_for_field


def filter_by_q(objs, q):
    """Filters a collection of objects by a Q object"""
    return [obj for obj in objs if obj_matches_q(obj, q)]


def obj_matches_q(obj, q):
    """Returns True if obj matches the Q object"""

    does_it_match = q.connector == q.AND
    for child in q.children:
        if isinstance(child, Q):
            r = obj_matches_q(obj, child)
        else:
            filter_statement, value = child
            r = obj_matches_filter_statement(obj, filter_statement, value)

        if q.connector == q.AND and not r:
            does_it_match = False
            break
        elif q.connector == q.OR and r:
            does_it_match = True
            break

    if q.negated:
        does_it_match = not does_it_match

    return does_it_match


def obj_matches_filter_statement(obj, filter_statement, filter_value):
    """Returns True if the obj matches the filter statement"""
    data_path, lookup = split_data_path_from_lookup(filter_statement)

    # todo: handle related object filtering
    if len(data_path) != 1:
        return

    if isinstance(obj, models.Model):
        model = type(obj)
        field = model._meta.get_field(data_path[0])
        obj_value = getattr(obj, data_path[0])
        assert_is_valid_lookup_for_field(lookup, field)
        try:
            filter_value, lookup = prep_filter_value_and_lookup(model, filter_statement, filter_value)
        except NoOpFilterException:
            return True

        return evaluate_lookup(lookup, obj_value, filter_value)


def prep_filter_value_and_lookup(model, filter_statement, filter_value):
    """
    Prepare the filter value and lookup for execution in python

    Converts the filter value to the appropriate type to be used in the query.

    In some cases the lookup may be changed to a more appropriate lookup.
    """
    qs = model.objects.filter(**{filter_statement: filter_value})
    try:
        filter_value = qs.query.where.children[0].rhs
        lookup = qs.query.where.children[0].lookup_name
    except IndexError:
        # the filter was a no-op
        raise NoOpFilterException()

    return filter_value, lookup


def split_data_path_from_lookup(filter_statement):
    statement_parts = filter_statement.split('__')
    if len(statement_parts) == 1:
        lookup = 'exact'
    elif len(statement_parts) > 1:
        lookup = statement_parts[-1]
        if lookup not in SUPPORTED_LOOKUP_NAMES:
            lookup = 'exact'

        if lookup == statement_parts[-1]:
            statement_parts.pop()

    return statement_parts, lookup
