# coding=utf-8
import unittest

from django.db.models.query_utils import Q
from django.test.testcases import TransactionTestCase, TestCase
from django.utils import timezone
from qtools import obj_matches_q, filter_by_q
from qtools.exceptions import InvalidLookupUsage
from qtools.lookups import SUPPORTED_LOOKUP_NAMES

from main.models import MiscModel
from .base import QInPythonTestCaseMixin


class TestLookups(TestCase, QInPythonTestCaseMixin):
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
            obj_matches_q(m, Q(text__regex=[1, 2, 3]))

    def test_week_days(self):
        now = timezone.now()
        for day in range(0, 8):
            self.assert_lookup_works('week_day', 'datetime', now, day)

    def test_case_sensitivity(self):
        m = MiscModel(text='a')
        assert obj_matches_q(m, Q(text__iexact='A'))
        assert not obj_matches_q(m, Q(text__exact='A'))


class TestLookupsBulk(TransactionTestCase, QInPythonTestCaseMixin):
    @unittest.skip("Takes too long to run")
    def test_all_lookups_basic(self):
        field_names = ['nullable_boolean', 'boolean', 'integer', 'float', 'decimal', 'text', 'date', 'datetime', 'foreign', 'many']
        test_values = list(self.generate_test_value_pairs())
        lookup_names = SUPPORTED_LOOKUP_NAMES

        self.assert_lookups_work(field_names, lookup_names, test_values, fail_fast=False, skip_first=0)
