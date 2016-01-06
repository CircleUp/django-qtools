from django.db import models
from django.db.models.fields.related import ForeignObjectRel
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q

from utils import get_field_simple_datatype
from .exceptions import NoOpFilterException
from .lookups import get_lookup_adapter
from .utils import assert_is_valid_lookup_for_field, django_instances_to_keys


def filter_by_q(objs, q, lookup_adapter=None):
    """Filters a collection of objects by a Q object"""
    return [obj for obj in objs if obj_matches_q(obj, q)]


def obj_matches_q(obj, q, lookup_adapter=None):
    """Returns True if obj matches the Q object"""

    does_it_match = q.connector == q.AND
    for child in q.children:
        if isinstance(child, Q):
            r = obj_matches_q(obj, child)
        else:
            filter_statement, value = child
            r = obj_matches_filter_statement(obj, filter_statement, value, lookup_adapter)

        if q.connector == q.AND and not r:
            does_it_match = False
            break
        elif q.connector == q.OR and r:
            does_it_match = True
            break

    if q.negated:
        does_it_match = not does_it_match

    return does_it_match


def get_model_attribute_values_by_db_name(obj, name, lookup_adapter=None):
    model = type(obj)
    field = model._meta.get_field(name)
    if isinstance(field, ForeignObjectRel):
        accessor_name = field.get_accessor_name()
        try:
            manager_or_obj = getattr(obj, accessor_name)
        except model.DoesNotExist:
            return []
        if isinstance(manager_or_obj, models.Manager):
            return list(manager_or_obj.all())
        else:
            return [manager_or_obj]
    else:
        return [getattr(obj, name)]


def obj_matches_filter_statement(obj, filter_statement, filter_value, lookup_adapter=None):
    """Returns True if the obj matches the filter statement"""
    next_token, remaining_statement_parts = process_filter_statement(filter_statement)
    lookup = remaining_statement_parts[-1]
    lookup_adapter = get_lookup_adapter(lookup_adapter)
    if obj is None:
        return lookup_adapter.evaluate_lookup(lookup, obj, filter_value)

    # handle QuerySets as arguments
    if isinstance(filter_value, QuerySet):
        filter_value = list(filter_value)

    if not isinstance(obj, models.Model):
        raise Exception("Only django objects supported for now. %s" % str(obj))

    model = type(obj)
    opts = model._meta
    field = opts.get_field(next_token)

    if len(remaining_statement_parts) == 1:
        simple_type = get_field_simple_datatype(field)
        assert_is_valid_lookup_for_field(lookup, simple_type)

        try:
            filter_value, lookup = prep_filter_value_and_lookup(model, filter_statement, filter_value)
        except NoOpFilterException:
            return True

        obj_values = get_model_attribute_values_by_db_name(obj, next_token)
        obj_values = django_instances_to_keys(*obj_values)
        for obj_value in obj_values:
            r = lookup_adapter.evaluate_lookup(lookup, obj_value, filter_value, simple_type)
            if r:
                return True
        return False

    obj_values = get_model_attribute_values_by_db_name(obj, next_token)

    for o in obj_values:
        result = obj_matches_filter_statement(o, '__'.join(remaining_statement_parts), filter_value)
        if result:
            return True


def prep_filter_value_and_lookup(model, filter_statement, filter_value):
    """
    Prepare the filter value and lookup for execution in python

    Converts the filter value to the appropriate type to be used in the query.

    In some cases the lookup may be changed to a more appropriate lookup.
    """
    qs = model.objects.filter(**{filter_statement: filter_value})

    try:
        lookup = qs.query.where.children[0].lookup_name
        if lookup == 'in' and isinstance(filter_value, basestring):
            pass
        else:
            filter_value = qs.query.where.children[0].rhs

    except IndexError:
        # the filter was a no-op
        raise NoOpFilterException()
    return filter_value, lookup


def process_filter_statement(filter_statement):
    statement_parts = filter_statement.split('__')

    lookup = statement_parts[-1]
    lookup_adapter = get_lookup_adapter()
    if lookup not in lookup_adapter.SUPPORTED_LOOKUP_NAMES:
        lookup = 'exact'

    if lookup != statement_parts[-1]:
        statement_parts.append(lookup)

    next_token = statement_parts[0]
    del statement_parts[0]

    return next_token, statement_parts
