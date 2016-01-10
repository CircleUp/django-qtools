# coding=utf-8
import unittest
from datetime import timedelta

from django.db.models.query_utils import Q
from django.test.testcases import TransactionTestCase, TestCase
from django.utils import timezone
from qtools import obj_matches_q, filter_by_q
from qtools.exceptions import InvalidLookupUsage
from qtools.lookups import get_lookup_adapter

from main.models import MiscModel
from .base import QInPythonTestCaseMixin


class TestLookups(TestCase, QInPythonTestCaseMixin):
    def test_func_exists_for_each_supported_lookup(self):
        lookup_adapter = get_lookup_adapter()
        for func_name in lookup_adapter.SUPPORTED_LOOKUP_NAMES:
            lookup_adapter.get_lookup_function(func_name)

    def test_in_with_queryset_as_arg(self):
        main = MiscModel()
        main.save()

        MiscModel(foreign=main, integer=1, text='a').save()
        MiscModel(foreign=main, integer=2, text='a').save()
        MiscModel(foreign=main, integer=3, text='b').save()
        MiscModel(foreign=main, integer=4, text='b').save()

        a_models = MiscModel.objects.filter(text='a')

        all_models = list(MiscModel.objects.all())

        db_results = MiscModel.objects.filter(miscmodel__in=a_models)
        mem_results = filter_by_q(all_models, Q(miscmodel__in=a_models))
        self.assertEqual(set(db_results), set(mem_results))

    def test_invalid_usage_regex(self):
        m = MiscModel()
        m.save()
        with self.assertRaisesRegexp(InvalidLookupUsage, 'string'):
            obj_matches_q(m, Q(text__regex=[1, 2, 3]), lookup_adapter='python')

    def test_week_days(self):
        now = timezone.now()
        for delta in range(0, 8):
            dt = now - timedelta(days=delta)
            for day in range(0, 8):
                self.assert_lookup_matches_db_execution('week_day', 'datetime', dt, day)


class TestLookupValues(TestCase, QInPythonTestCaseMixin):
    def test_date_year(self):
        self.run_through_lookup_test_cases(
            field_name='date',
            lookup_name='year',
            test_values_and_expectations=[
                (None, False, Exception, Exception),
            ]
        )

    def test_datetime_year(self):
        self.run_through_lookup_test_cases(
            field_name='datetime',
            lookup_name='year',
            test_values_and_expectations=[
                (None, 2, False, Exception),
                (None, 1, False, Exception),
                (timezone.now(), 1, False, Exception),
            ]
        )

    def test_datetime_gte(self):
        now = timezone.now()
        self.run_through_lookup_test_cases(
            field_name='datetime',
            lookup_name='gte',
            test_values_and_expectations=[
                (now, now, True, True),
            ]
        )

    def test_decimal_exact(self):
        self.run_through_lookup_test_cases(
            field_name='decimal',
            lookup_name='exact',
            test_values_and_expectations=[
                (1.0, 1, True, True),
            ]
        )

    def test_decimal_in(self):
        self.run_through_lookup_test_cases(
            field_name='decimal',
            lookup_name='in',
            test_values_and_expectations=[
                (True, '1', True, True),
            ]
        )

    def test_float_gt(self):
        self.run_through_lookup_test_cases(
            field_name='float',
            lookup_name='gt',
            test_values_and_expectations=[
                (-0.3, -0.3, False, False),
                (-0.3333, -0.3333, False, False),
                (-0.3333333333333333333333333333, -0.3333333333333333333333333333, False, False),
                (-0.333333333, -0.333333334, True, True),
                (-0.333333333333333333, -0.333333333333333334, False, False)  # too long to be meaningful difference
            ]
        )

    def test_float_in(self):
        self.run_through_lookup_test_cases(
            field_name='decimal',
            lookup_name='in',
            test_values_and_expectations=[
                (True, '1', True, True),
            ]
        )

    def test_float_month(self):
        self.run_through_lookup_test_cases(
            field_name='float',
            lookup_name='month',
            test_values_and_expectations=[
                (False, '', Exception, Exception),
            ]
        )

    def test_integer_in(self):
        self.run_through_lookup_test_cases(
            field_name='decimal',
            lookup_name='in',
            test_values_and_expectations=[
                (True, '1', True, True),
            ]
        )

    def test_nullable_boolean_isnull(self):
        self.run_through_lookup_test_cases(
            field_name='nullable_boolean',
            lookup_name='isnull',
            test_values_and_expectations=[
                (True, ' ', False, False),
            ]
        )

    def test_nullable_boolean_in(self):
        self.run_through_lookup_test_cases(
            field_name='nullable_boolean',
            lookup_name='in',
            test_values_and_expectations=[
                ('1', '0.0', False, False)
            ]
        )

    def test_text_contains(self):
        self.run_through_lookup_test_cases(
            field_name='text',
            lookup_name='contains',
            test_values_and_expectations=[
                (None, 0.0, False, False),
                (True, True, True, True),
                ('True', ' ', False, False),
            ]
        )

    def test_text_endswith(self):
        self.run_through_lookup_test_cases(
            field_name='text',
            lookup_name='endswith',
            test_values_and_expectations=[
                (True, ' ', False, False),
            ]
        )

    def test_text_iexact(self):
        m = MiscModel(text='a')
        assert obj_matches_q(m, Q(text__iexact='A'), lookup_adapter='python')
        assert not obj_matches_q(m, Q(text__exact='A'), lookup_adapter='python')

    def test_text_gt(self):
        with self.assertRaisesRegexp(InvalidLookupUsage, 'collation'):
            self.run_through_lookup_test_cases(
                field_name='text',
                lookup_name='gt',
                test_values_and_expectations=[
                    (None, 'e', False, False),
                    ('True', 'a', False, True),
                    ('true', 'a', True, True),
                    ('True', 'True', False, False)
                ]
            )

    def test_text_in(self):
        self.run_through_lookup_test_cases(
            field_name='text',
            lookup_name='in',
            test_values_and_expectations=[
                ('ab', ['ab', 'ac'], True, True),
                ('ab   ', ['ab ', 'ac'], False, True),
                ('ab', 'ab', False, False),
                ('', ' ', False, True),
                (' ', [None, ''], False, True),
                ('A', 'False', False, True),
                ('a', 'A', False, True),
                ('A', 'A', True, True),
                (2.0, 2.0, Exception, Exception),
                (2.0, [], False, False),
                (0.0, '0.0', False, False),
                ('True', (True,), True, True),
            ]
        )

    def test_text_regex(self):
        self.run_through_lookup_test_cases(
            field_name='text',
            lookup_name='regex',
            test_values_and_expectations=[
                (None, '', False, Exception),
                (None, ' ', False, False),
                ('a', [], Exception, Exception)
            ]
        )

    def test_text_iregex(self):
        self.run_through_lookup_test_cases(
            field_name='text',
            lookup_name='iregex',
            test_values_and_expectations=[
                (None, '', False, Exception),
                (None, ' ', False, False),
                ('a', [], Exception, Exception),
                ('(1, 3)', 1.0, Exception, Exception),
                ('-1', -1.0, Exception, Exception)
            ]
        )


class TestLookupsBulk(TransactionTestCase, QInPythonTestCaseMixin):
    @unittest.skip("Takes too long to run")
    def test_all_lookups_basic(self):
        """

        This will return failures. Specifically:
          - python doesn't collate the same way as mysql so string comparisons will come out different  ('True' > '[]' for example)
          - fulltext search will throw errors on sqlite because it isn't supported (hardcoded to skip these tests)
          - fulltext search will throw errors on mysql if there isn't a fulltext index (hardcoded to skip these tests)
        """
        lookup_adapter = get_lookup_adapter()
        field_names = ['nullable_boolean', 'boolean', 'integer', 'float', 'decimal', 'text', 'date', 'datetime', 'foreign', 'many']
        test_values = list(self.generate_test_value_pairs())
        lookup_names = lookup_adapter.SUPPORTED_LOOKUP_NAMES

        self.assert_lookups_work(field_names, lookup_names, test_values, fail_fast=False, skip_first=0)
