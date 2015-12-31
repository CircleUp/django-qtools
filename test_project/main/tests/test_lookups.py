# coding=utf-8
import datetime
from decimal import InvalidOperation
import itertools
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.query_utils import Q
from django.test.testcases import TransactionTestCase
from django.utils import timezone
from qtools.lookups import SUPPORTED_LOOKUP_NAMES
from qtools.pyq import obj_matches_q, InvalidLookupUsage
from main.models import MiscModel


class QInPythonTestCase(TransactionTestCase):
    def assert_lookup_works(self, lookup_name, field_name, obj_value, filter_value, fail_fast=False):
        obj_value = create_test_value(obj_value)
        filter_value = create_test_value(filter_value)
        fail_msg = "Failed: (%s)%s__%s=%s  <db-result: %s> != <py-result: %s> saved_db_value=%s sql: %s"

        try:
            with transaction.atomic():
                m = MiscModel(**{field_name: obj_value})
                m.save()
                saved_m = MiscModel.objects.get(id=m.id)
                saved_value = getattr(saved_m, field_name)

        except (IntegrityError, ValueError, ValidationError, TypeError, ValueError, InvalidOperation):
            # we aren't testing which field values are valid to save in the db
            transaction.rollback()
            return None
        lookup = field_name + '__' + lookup_name
        q = Q(**{lookup: filter_value})
        py_e = db_e = None
        db_query = ''
        try:
            qs = MiscModel.objects.filter(q)
            db_matches = len(qs.filter(id=m.id)) == 1
            try:
                db_query = str(qs.query)
            except Exception, e:
                pass

        except Exception, db_e:
            db_matches = db_e.__class__
            db_matches = 'Exception'

        is_valid_exception = False

        try:
            py_matches = obj_matches_q(saved_m, q)
        except Exception, py_e:
            py_matches = py_e.__class__
            py_matches = 'Exception'
            if py_e.__class__ == InvalidLookupUsage:
                # while the django doesn't throw an exception, it really should
                is_valid_exception = True

        if db_matches != py_matches and not is_valid_exception:
            msg = fail_msg % (
                repr(obj_value), field_name, lookup_name,
                repr(filter_value), repr(db_matches),
                repr(py_matches), repr(saved_value),
                db_query
            )
            print "\n" + msg
            if py_e:
                print py_e
            if db_e:
                print db_e

            if fail_fast:
                qs = MiscModel.objects.filter(q)
                db_matches = len(qs.filter(id=m.id)) == 1
                obj_matches_q(saved_m, q)
            MiscModel.objects.all().delete()
            return msg
        MiscModel.objects.all().delete()

    def assert_lookups_work(self, model, field_names, lookup_names, test_values, fail_fast=False, skip_first=0):
        failed_test_msgs = []
        passed_test_msgs = []
        error_args = []
        test_count = 0
        num_tests = len(test_values) * len(lookup_names) * len(field_names)
        print "Running %i tests total" % num_tests
        for lookup_name in lookup_names:
            print "Running %i tests for %s lookup" % (len(test_values) * len(field_names), lookup_name)
            for field_name in field_names:
                for obj_value, filter_value in test_values:
                    test_count += 1
                    if test_count < skip_first:
                        continue

                    print '%i/%i      Passed: %i  Failed: %i            \r' % (
                        test_count, num_tests, len(passed_test_msgs), len(failed_test_msgs)),

                    error_msg = self.assert_lookup_works(lookup_name, field_name, obj_value, filter_value, fail_fast=fail_fast)
                    if error_msg:
                        error_args.append((lookup_name, field_name, obj_value, filter_value))
                        failed_test_msgs.append(error_msg)
                        if fail_fast:
                            raise Exception('test failed')
                    else:
                        passed_msg = 'Passed: (%s)%s__%s=%s' % (repr(obj_value), field_name, lookup_name, repr(filter_value))
                        passed_test_msgs.append(passed_msg)
        print "Passed %s lookup tests and failed %s tests." % (len(passed_test_msgs), len(failed_test_msgs))
        if failed_test_msgs:
            print ',\n'.join([repr(e) for e in error_args])
            raise Exception('\n' + '\n'.join(failed_test_msgs[:1000]))

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
        return itertools.product(interesting_values, repeat=2)


class TestLookups(QInPythonTestCase):
    def test_many_to_many(self):
        raise NotImplemented()

    def test_related_object(self):
        raise NotImplemented()

    def test_third_degree_related_object(self):
        raise NotImplemented()

    def test_invalid_usage_regex(self):
        m = MiscModel()
        m.save()
        with self.assertRaisesRegexp(InvalidLookupUsage, 'string'):
            obj_matches_q(m, Q(text__regex=[1, 2, 3]))

    def test_all_lookups_basic(self):
        field_names = ['nullable_boolean', 'boolean', 'integer', 'float', 'decimal', 'text', 'date', 'datetime', 'foreign', 'many']
        test_values = list(self.generate_test_value_pairs())
        lookup_names = SUPPORTED_LOOKUP_NAMES

        self.assert_lookups_work(MiscModel, field_names, lookup_names, test_values, fail_fast=False, skip_first=0)


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
