# coding=utf-8
import datetime
from decimal import InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.db.utils import DataError
from django.utils import timezone
from qtools import filter_by_q
from qtools.exceptions import InvalidLookupUsage, InvalidLookupValue, InvalidFieldLookupCombo
from qtools.filterq import obj_matches_filter_statement

from main.models import MiscModel

MATCHES_NOTHING = object()
NOT_SET = object()


class DoesNotMatchDbExecution(Exception):
    def __init__(self, q, db_result, py_result, sql):
        self.q = q
        self.db_result = db_result
        self.py_result = py_result
        self.sql = str(sql)

    def __str__(self):
        fail_msg = "%s did not execute the same in db and python  <db-result: %s> != <py-result: %s>  sql: %s"
        return fail_msg % (repr(self.q), repr(self.db_result), repr(self.py_result), self.sql)


class LookupDoesNotMatchDbExecution(DoesNotMatchDbExecution):
    def __init__(self, lookup_name, field_name, obj_value, filter_value, db_result, py_result, saved_db_value, sql):
        self.lookup_name = lookup_name
        self.field_name = field_name
        self.obj_value = obj_value
        self.filter_value = filter_value
        self.db_result = db_result
        self.py_result = py_result
        self.saved_db_value = saved_db_value
        self.sql = str(sql)

    def __str__(self):
        fail_msg = "Failed: (%s)%s__%s=%s  <db-result: %s> != <py-result: %s> saved_db_value=%s sql: %s"
        return fail_msg % (
            repr(self.obj_value), self.field_name, self.lookup_name,
            repr(self.filter_value), repr(self.db_result),
            repr(self.py_result), repr(self.saved_db_value),
            self.sql
        )


class InvalidDbState(Exception):
    pass


class QInPythonTestCaseMixin(object):
    def assert_lookup_matches(self, lookup_name, field_name, obj_value, filter_value, lookup_adapter=None, expected=True):
        m = MiscModel(**{field_name: obj_value})
        filter_statement = field_name + '__' + lookup_name
        try:
            result = obj_matches_filter_statement(m, filter_statement, filter_value, lookup_adapter=lookup_adapter)

        except Exception, e:
            if type(expected) != type or not isinstance(e, expected):
                raise
                # raise Exception('Unexpected result for (%s)%s==%s Expected: %s Actual: %s' % (repr(obj_value), filter_statement, repr(filter_value), repr(expected), repr(e)))
        else:
            if result != expected:
                raise Exception(
                    'Unexpected result for %s lookup (%s)%s==%s Expected: %s Actual: %s' % (repr(lookup_adapter), repr(obj_value), filter_statement, repr(filter_value), repr(expected), repr(result)))

    def assert_lookup_does_not_match(self, lookup_name, field_name, obj_value, filter_value, lookup_adapter=None):
        return self.assert_lookup_matches(lookup_name, field_name, obj_value, filter_value, lookup_adapter=lookup_adapter, expected=False)

    def assert_lookup_matches_db_execution(self, lookup_name, field_name, obj_value, filter_value, fail_fast=False, raise_invalid_usage=True):
        MiscModel.objects.all().delete()
        obj_value = create_test_value(obj_value)
        filter_value = create_test_value(filter_value)

        try:
            with transaction.atomic():
                m = MiscModel(**{field_name: obj_value})
                m.save()
                saved_m = MiscModel.objects.get(id=m.id)
                saved_value = getattr(saved_m, field_name)
        except (IntegrityError, ValueError, ValidationError, TypeError, ValueError, InvalidOperation, DataError), e:
            # we aren't testing which field values are valid to save in the db, so we'll skip these cases
            transaction.rollback()
            raise InvalidDbState(str(e))

        filter_statement = field_name + '__' + lookup_name

        q = Q(**{filter_statement: filter_value})

        try:
            self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q, raise_original_exceptions=fail_fast, raise_invalid_usage=raise_invalid_usage)
        except DoesNotMatchDbExecution, e:
            raise LookupDoesNotMatchDbExecution(
                lookup_name=lookup_name,
                field_name=field_name,
                obj_value=obj_value,
                filter_value=filter_value,
                db_result=e.db_result,
                py_result=e.py_result,
                saved_db_value=saved_value,
                sql=e.sql
            )

    def assert_lookups_work(self, field_names, lookup_names, test_values, fail_fast=False, skip_first=0):
        does_not_match_db_exceptions = []
        invalid_usage_exception_count = 0
        invalid_db_state_count = 0
        tested_and_passed_count = 0
        status_msg = '\rTesting %s__%s.  Total Progress: %i/%i  Invalid DB State: %i  Invalid Usage: %i  DBMatchProblem: %i  Passed: %i  Off By: %i               '
        test_count = 0
        num_tests = len(test_values) * len(test_values) * len(lookup_names) * len(field_names)
        print "Running %i tests total" % num_tests
        print"Running %i tests for per lookup" % (len(test_values) * len(test_values) * len(field_names))
        for lookup_name in lookup_names:
            for field_name in field_names:
                skip_field_name = MATCHES_NOTHING
                print ''
                for obj_value in test_values:
                    skip_obj_value = MATCHES_NOTHING
                    for filter_value in test_values:
                        test_count += 1

                        if lookup_name == 'search' and field_name == 'text':
                            # doesn't work.
                            continue

                        if test_count < skip_first:
                            continue

                        if obj_value == skip_obj_value:
                            # this value cannot be saved to db in this type of field, skip it
                            invalid_db_state_count += 1
                            continue

                        if field_name == skip_field_name:
                            # this field_name / lookup combo is not valid, skip it
                            invalid_usage_exception_count += 1
                            continue
                        checksum = invalid_db_state_count + invalid_usage_exception_count + len(does_not_match_db_exceptions) + tested_and_passed_count
                        discrepency = test_count - checksum
                        print status_msg % (
                            field_name, lookup_name, test_count, num_tests, invalid_db_state_count,
                            invalid_usage_exception_count, len(does_not_match_db_exceptions), tested_and_passed_count,
                            discrepency
                        ),
                        try:
                            self.assert_lookup_matches_db_execution(lookup_name, field_name, obj_value, filter_value, fail_fast=fail_fast)
                        except InvalidDbState:
                            invalid_db_state_count += 1
                            skip_obj_value = obj_value
                        except InvalidLookupValue:
                            invalid_usage_exception_count += 1
                        except InvalidFieldLookupCombo:
                            skip_field_name = field_name
                            invalid_usage_exception_count += 1
                        except InvalidLookupUsage:
                            invalid_usage_exception_count += 1
                        except DoesNotMatchDbExecution, e:
                            does_not_match_db_exceptions.append(e)
                            print ''
                            print e
                            if fail_fast:
                                raise
                        else:
                            tested_and_passed_count += 1
        print ''
        print "Passed %s lookup tests and failed %s tests." % (tested_and_passed_count, len(does_not_match_db_exceptions))
        if does_not_match_db_exceptions:
            raise Exception(',\n'.join([str(e) for e in does_not_match_db_exceptions]))

    def run_through_lookup_test_cases(self, field_name, lookup_name, test_values_and_expectations):
        for obj_value, filter_value, expected, expected_mysql in test_values_and_expectations:
            self.assert_lookup_matches(
                field_name=field_name,
                lookup_name=lookup_name,
                obj_value=obj_value,
                filter_value=filter_value,
                expected=expected,
                lookup_adapter='python'
            )

        for obj_value, filter_value, expected, expected_mysql in test_values_and_expectations:
            self.assert_lookup_matches(
                field_name=field_name,
                lookup_name=lookup_name,
                obj_value=obj_value,
                filter_value=filter_value,
                expected=expected_mysql,
                lookup_adapter='mysql'
            )

        for obj_value, filter_value, expected, expected_mysql in test_values_and_expectations:
            try:
                self.assert_lookup_matches_db_execution(
                    field_name=field_name,
                    lookup_name=lookup_name,
                    obj_value=obj_value,
                    filter_value=filter_value,
                    fail_fast=True,
                    raise_invalid_usage=False
                )
            except InvalidLookupUsage:
                pass

    def generate_test_value_pairs(self):
        now = datetime.datetime.now()
        now_tz = timezone.now()
        today = datetime.date.today()

        interesting_values = [
            None,

            # Boolean
            True,
            False,
            'True',
            'False',

            # Integer
            0,
            1,
            2,
            -1,
            -2,
            111222333,
            -111222333,
            '1',
            '-1',
            '0',

            # Float
            0.0,
            '0.0',
            1.0,
            2.0,
            '2.0',
            1.0 / 3.0,
            -1.0,
            -2.0,
            -2.000,
            '-2.0',
            -1.0 / 3.0,

            # String
            '',
            ' ',
            'a',
            'A',
            'long string long string long string long string long string long string long string long string long string ',

            # unicode handling
            u'',
            u'☺',

            # date objects
            today,

            # datetime objects
            now,
            now_tz,

            # iterables
            tuple(),
            list(),
            (1, 3),
            (5, 6),
            ('a',),
            [None, ''],
            (True,),

            # python objects
            # 'TestValue: object',

            # django model objects
            'TestValue: unsaved_model',
            'TestValue: saved_model',
        ]
        return interesting_values

    def assert_q_executes_the_same_in_python_and_sql(self, model, q, expected_count=NOT_SET, raise_original_exceptions=False, lookup_adapter=None, raise_invalid_usage=True):
        all_objs = list(model.objects.all())

        try:
            qs = model.objects.filter(q)
            db_result = list(qs)
        except Exception, db_result:
            pass

        try:
            mem_result = filter_by_q(all_objs, q, lookup_adapter=lookup_adapter)
        except InvalidLookupUsage, mem_result:
            if raise_invalid_usage:
                raise
        except Exception, mem_result:
            pass

        if isinstance(db_result, Exception) and isinstance(mem_result, Exception):
            return

        if raise_original_exceptions and (isinstance(db_result, Exception) or isinstance(mem_result, Exception)):
            raise

        if set(db_result) != set(mem_result):
            try:
                sql = str(qs.query)
            except:
                sql = ''

            raise DoesNotMatchDbExecution(
                q=q,
                db_result=db_result,
                py_result=mem_result,
                sql=sql
            )

        if expected_count != NOT_SET and expected_count != len(mem_result):
            raise Exception('Did not behave as expected.')


def create_test_value(value):
    if isinstance(value, basestring) and value.startswith('TestValue: '):
        value_type = value.replace('TestValue: ', '')
        if value_type == 'object':
            return object()
        elif value_type == 'saved_model':
            saved_model = MiscModel()
            saved_model.save()
            return saved_model
        elif value_type == 'unsaved_model':
            return MiscModel()

    return value
