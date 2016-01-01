# coding=utf-8
import datetime
from decimal import InvalidOperation
from exceptions import NotImplementedError

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.query_utils import Q
from django.test.testcases import TransactionTestCase
from django.utils import timezone
from qtools.exceptions import InvalidFieldLookupCombo, InvalidLookupUsage, InvalidLookupValue
from qtools.filterq import obj_matches_q, filter_by_q
from qtools.lookups import SUPPORTED_LOOKUP_NAMES

from main.models import MiscModel

MATCHES_NOTHING = object()


class DoesNotMatchDbExecution(Exception):
    pass


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

    def description(self):
        fail_msg = "Failed: (%s)%s__%s=%s  <db-result: %s> != <py-result: %s> saved_db_value=%s sql: %s"
        return fail_msg % (
            repr(self.obj_value), self.field_name, self.lookup_name,
            repr(self.filter_value), repr(self.db_result),
            repr(self.py_result), repr(self.saved_db_value),
            self.sql
        )


class InvalidDbState(Exception):
    pass


class QInPythonTestCase(TransactionTestCase):
    def assert_lookup_works(self, lookup_name, field_name, obj_value, filter_value, fail_fast=False):
        MiscModel.objects.all().delete()
        obj_value = create_test_value(obj_value)
        filter_value = create_test_value(filter_value)

        try:
            with transaction.atomic():
                m = MiscModel(**{field_name: obj_value})
                m.save()
                saved_m = MiscModel.objects.get(id=m.id)
                saved_value = getattr(saved_m, field_name)

        except (IntegrityError, ValueError, ValidationError, TypeError, ValueError, InvalidOperation), e:
            # we aren't testing which field values are valid to save in the db, so we'll skip these cases
            transaction.rollback()
            raise InvalidDbState(str(e))
        filter_statement = field_name + '__' + lookup_name
        q = Q(**{filter_statement: filter_value})
        db_query = ''
        try:
            qs = MiscModel.objects.filter(q)
            db_matches = len(qs.filter(id=m.id)) == 1
            try:
                db_query = str(qs.query)
            except Exception:
                pass
        except Exception, db_e:
            db_matches = db_e

        try:
            py_matches = obj_matches_q(saved_m, q)
        except InvalidLookupUsage:
            raise
        except Exception, py_e:
            py_matches = py_e

        if isinstance(db_matches, Exception) and isinstance(py_matches, Exception):
            # both versions had an exception, which is okay
            return

        if db_matches == py_matches:
            # each type of execution had the same result
            return

        if fail_fast:
            # try to recreate the exception
            if isinstance(db_matches, Exception):
                qs = MiscModel.objects.filter(q)
                db_matches = len(qs.filter(id=m.id)) == 1
            if isinstance(py_matches, Exception):
                py_matches = obj_matches_q(saved_m, q)

        raise LookupDoesNotMatchDbExecution(
            lookup_name=lookup_name,
            field_name=field_name,
            obj_value=obj_value,
            filter_value=filter_value,
            db_result=db_matches,
            py_result=py_matches,
            saved_db_value=saved_value,
            sql=str(db_query)
        )

    def assert_lookups_work(self, field_names, lookup_names, test_values, fail_fast=False, skip_first=0):
        does_not_match_db_exceptions = []
        invalid_usage_exception_count = 0
        invalid_db_state_count = 0
        tested_and_passed_count = 0
        status_msg = '\rTesting %s_%s.  Total Progress: %i/%i  Invalid DB State: %i  Invalid Usage: %i  DBMatchProblem: %i  Passed: %i  Off By: %i               '
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
                            lookup_name, field_name, test_count, num_tests, invalid_db_state_count,
                            invalid_usage_exception_count, len(does_not_match_db_exceptions), tested_and_passed_count,
                            discrepency
                        ),

                        try:
                            self.assert_lookup_works(lookup_name, field_name, obj_value, filter_value, fail_fast=fail_fast)
                        except InvalidDbState:
                            invalid_db_state_count += 1
                            skip_obj_value = obj_value
                        except InvalidLookupValue:
                            invalid_usage_exception_count += 1
                        except InvalidFieldLookupCombo:
                            skip_field_name = field_name
                            invalid_usage_exception_count += 1
                        except DoesNotMatchDbExecution, e:
                            does_not_match_db_exceptions.append(e)
                            print ''
                            print e, e.description()
                            if fail_fast:
                                raise
                        else:
                            tested_and_passed_count += 1
        print ''
        print "Passed %s lookup tests and failed %s tests." % (tested_and_passed_count, len(does_not_match_db_exceptions))
        if does_not_match_db_exceptions:
            raise Exception(',\n'.join([e.description() for e in does_not_match_db_exceptions]))

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

    def assert_q_executes_the_same_in_python_and_sql(self, model, q):
        all = model.objects.all()
        db_filtered = model.objects.filter(q)
        mem_filtered = filter_by_q(all, q)
        if set(db_filtered) != set(mem_filtered):
            raise DoesNotMatchDbExecution("%s != %s" % (repr(db_filtered), repr(mem_filtered)))


class TestLookups(QInPythonTestCase):
    def test_nested_q_object_handling(self):
        m1 = MiscModel(text='hello', integer=5)
        m1.save()

        m2 = MiscModel(text='goodbye', integer=50)
        m2.save()

        q = Q(text='hola') | (Q(integer__gt=49) & Q(text='goodbye') & Q(integer__lt=500)) | Q(text__gt='zzzzzzzzzzzzz')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

    def test_q_negation(self):
        MiscModel(text='hello', integer=5).save()
        MiscModel().save()

        q = ~Q(text='hello')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = ~Q(text='goodbye')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)


    def test_many_to_many(self):
        raise NotImplementedError()

    def test_related_object(self):
        raise NotImplementedError()

    def test_third_degree_related_object(self):
        raise NotImplementedError()

    def test_invalid_usage_regex(self):
        m = MiscModel()
        m.save()
        with self.assertRaisesRegexp(InvalidLookupUsage, 'string'):
            obj_matches_q(m, Q(text__regex=[1, 2, 3]))

    def test_week_days(self):
        now = timezone.now()
        for day in range(0, 8):
            self.assert_lookup_works('week_day', 'datetime', now, day)

    def test_case_sensitivity(self):
        pass

    def test_all_lookups_basic(self):
        field_names = ['nullable_boolean', 'boolean', 'integer', 'float', 'decimal', 'text', 'date', 'datetime', 'foreign', 'many']
        test_values = list(self.generate_test_value_pairs())
        lookup_names = SUPPORTED_LOOKUP_NAMES

        self.assert_lookups_work(field_names, lookup_names, test_values, fail_fast=False, skip_first=0)


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
