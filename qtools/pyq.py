from django.db import models
from .lookups import evaluate_lookup, SUPPORTED_LOOKUP_NAMES
from .utils import assert_is_valid_lookup_for_field
from .exceptions import InvalidLookupUsage, NoOpFilterException

def filter_objs_by_q(objs, q):
    return [obj for obj in objs if obj_matches_q(obj, q)]


def obj_matches_q(obj, q):
    for child in q.children:
        filter_statement, value = child
        r = obj_matches_filter_statement(obj, filter_statement, value)

        if q.connector == q.AND and not r:
            return False
        elif q.connector == q.OR and r:
            return True

        return (q.connector == q.AND)


def obj_matches_filter_statement(obj, filter_statement, filter_value):
    data_path, lookup = split_data_path_from_lookup(filter_statement)

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


_DB_TYPES_SIMPLE_MAP = {
    'bool': 'boolean',
    'integer': 'number',
    'float': 'number',
    'real': 'number',
    'decimal': 'number',
    'text': 'string',
    'datetime': 'datetime',
    'date': 'date'
}


def simplify_data_types(db_field_type):
    if 'varchar' in db_field_type:
        return 'string'

    return _DB_TYPES_SIMPLE_MAP.get(db_field_type, db_field_type)
