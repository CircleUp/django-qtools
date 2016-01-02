"""

* todo
 - Figure out how to have test models that don't depend on CircleUp's models
"""
from __future__ import unicode_literals

from django.db import models
from django.test.testcases import TestCase

from qtools import nested_q, q_method, QMethodQuerySet
# from main.models.company import Company
# from main.models.investment import Investment
# from main.tests.model_factories.misc import InvestmentFactory
# from main.tests.model_factories.company import CompanyFactory
# from main.tests.utils import CircleUpTestCase


class DbMethodDecoratorTests(TestCase):

    def test_q_method_with_args(self):
        """Test whether q method can handle args and kwargs"""

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestCompanyQuerySet(QMethodQuerySet):
            @q_method
            def raised_between(Q, lower, upper=None):
                if not upper:
                    upper = lower + 10000000000000
                return Q(raise_amount_received_online__gt=lower, raise_amount_received_online__lt=upper)

        class TestCompany(Company):
            objects = TestCompanyQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        amount = 10000

        company = CompanyFactory.create()
        company = TestCompany.objects.get(pk=company.pk)
        company.raise_amount_received_online = amount
        company.save()

        # test various combinations of args and kwargs on the manager method
        self.assertEqual(1, TestCompany.objects.raised_between(amount - 1).count())
        self.assertEqual(1, TestCompany.objects.raised_between(amount - 1, amount + 1).count())
        self.assertEqual(1, TestCompany.objects.raised_between(amount - 1, upper=amount + 1).count())
        self.assertEqual(1, TestCompany.objects.raised_between(lower=amount - 1, upper=amount + 1).count())
        self.assertEqual(0, TestCompany.objects.raised_between(amount + 1).count())
        self.assertEqual(0, TestCompany.objects.raised_between(lower=amount + 1, upper=amount + 2).count())

        # test various combinations of args and kwargs on the queryset method
        self.assertEqual(1, TestCompany.objects.all().raised_between(amount - 1).count())
        self.assertEqual(1, TestCompany.objects.all().raised_between(amount - 1, amount + 1).count())
        self.assertEqual(1, TestCompany.objects.all().raised_between(amount - 1, upper=amount + 1).count())
        self.assertEqual(1, TestCompany.objects.all().raised_between(lower=amount - 1, upper=amount + 1).count())
        self.assertEqual(0, TestCompany.objects.all().raised_between(amount + 1).count())
        self.assertEqual(0, TestCompany.objects.all().raised_between(lower=amount + 1, upper=amount + 2).count())

    def test_q_method_used_from_other_model(self):
        """
        Use a @q_method from a different model in a queryset

        This test is a good example of a plausible use case for this.
        """

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestCompanyQuerySet(QMethodQuerySet):
            @q_method
            def is_open(Q):
                return Q(creation_state=Company.RAISE_OPEN, deal_by_deal_circle__isnull=True) & ~Q(type_of_fund=Company.FUND_TYPE_CU_CAPITAL)

        class TestCompany(Company):
            objects = TestCompanyQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class InvestmentQuerySet(QMethodQuerySet):
            @q_method
            def from_open_company(Q):
                return nested_q('company', TestCompany.objects.is_open.q())

            def investments_in_open_companies(self):
                return self.filter(company__qmatches=TestCompany.objects.is_open.q())

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestInvestment(Investment):
            objects = InvestmentQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        investment = InvestmentFactory.create()
        investment = TestInvestment.objects.get(pk=investment.pk)
        investment.company.creation_state = Company.RAISE_OPEN
        investment.company.save()

        self.assertEqual(1, TestInvestment.objects.investments_in_open_companies().count())
        self.assertEqual(1, TestInvestment.objects.from_open_company().count())

        investment.company.creation_state = Company.RAISE_LEGALLY_CLOSED
        investment.company.save()
        self.assertEqual(0, TestInvestment.objects.investments_in_open_companies().count())
        self.assertEqual(0, TestInvestment.objects.from_open_company().count())

    def test_q_method_used_from_other_model_with_args(self):
        """
        Use a @q_method from a different model in a queryset
        """

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestCompanyQuerySet(QMethodQuerySet):
            @q_method
            def raised_between(Q, lower, upper=None):
                if not upper:
                    upper = lower + 10000000000000
                return Q(raise_amount_received_online__gt=lower, raise_amount_received_online__lt=upper)

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestCompany(Company):
            objects = TestCompanyQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        class InvestmentQuerySet(QMethodQuerySet):
            def companies_raised_more_than(self, lower):
                return self.filter(company__qmatches=TestCompany.objects.raised_between.q(lower))

        class TestInvestment(Investment):
            objects = InvestmentQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        investment = InvestmentFactory.create()
        investment = TestInvestment.objects.get(pk=investment.pk)
        investment.company.creation_state = Company.RAISE_OPEN
        investment.company.raise_amount_received_online = 100000
        investment.company.save()

        self.assertEqual(1, TestInvestment.objects.companies_raised_more_than(99999).count())
        self.assertEqual(0, TestInvestment.objects.companies_raised_more_than(100001).count())

        investment.company.raise_amount_received_online = 100
        investment.company.save()
        self.assertEqual(0, TestInvestment.objects.companies_raised_more_than(99999).count())
        self.assertEqual(0, TestInvestment.objects.companies_raised_more_than(100001).count())

    def test_q_method_on_queryset(self):
        """Can we use the q method on the queryset"""

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class CompanyQueryset(QMethodQuerySet):
            @q_method
            def raised_between(Q, lower, upper=None):
                if not upper:
                    upper = lower + 10000000000000
                return Q(raise_amount_received_online__gt=lower, raise_amount_received_online__lt=upper)

        class TestCompany(Company):
            objects = CompanyQueryset.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        class TestInvestment(Investment):
            objects = QMethodQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        amount_raised = 100000
        investment = InvestmentFactory.create(amount=10000)
        investment.company.raise_amount_received_online = amount_raised
        investment.company.save()

        self.assertEqual(1, TestCompany.objects.raised_between(amount_raised - 1, amount_raised + 1).count())  # on manager
        self.assertEqual(1, TestCompany.objects.all().raised_between(amount_raised - 1, amount_raised + 1).count())  # on queryset

        self.assertEqual(1, TestInvestment.objects.filter(company__qmatches=TestCompany.objects.raised_between.q(amount_raised - 1, amount_raised + 1)).count())
        self.assertEqual(0, TestInvestment.objects.filter(company__qmatches=TestCompany.objects.raised_between.q(amount_raised + 1, amount_raised + 2)).count())

    def test_valid_api_works(self):

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class InvestmentQuerySet(QMethodQuerySet):
            def companies_raised_more_than(self, lower):
                return self.filter(company__qmatches=TestCompany.objects.raised_between.q(lower))

            @q_method
            def bigger_than(Q, amount):
                return Q(amount__gt=amount)

            @q_method
            def bigger_than(Q, amount):
                return Q(amount__gt=amount)

        class TestInvestment(Investment):
            objects = InvestmentQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestCompanyQuerySet(QMethodQuerySet):
            @q_method
            def raising_gt(Q, amount):
                return Q(raise_amount_received_online__gt=amount)

            @q_method
            def raising_lt(Q, amount):
                return Q(raise_amount_received_online__lt=amount)

        class TestCompany(Company):
            objects = TestCompanyQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        InvestmentFactory.create(amount=6000)

        # valid api
        self.assertIsInstance(TestInvestment.objects.bigger_than(5000), models.QuerySet)
        self.assertIsInstance(TestInvestment.objects.bigger_than.q(5000), models.Q)
        TestInvestment.objects.filter(company__qmatches=TestCompany.objects.raising_gt.q(100000) & TestCompany.objects.raising_lt.q(200000))

        # invalid api
        with self.assertRaisesRegexp(TypeError, 'requires Q objects'):
            TestInvestment.objects.filter(company__qmatches=TestCompany.objects.raising_gt(100000).raising_gt(200000))  # qmatches requires Q objects

    def test_q_methods_do_not_leak_across_instances(self):
        """
        @q_methods should only be available on the queryset that has them defined.

        They should not be added at the class level or they'll leak between models.
        This was a horrible bug that took forever to debug.
        """

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class CompanyQueryset(QMethodQuerySet):
            @q_method
            def raised_between(Q, lower, upper=None):
                if not upper:
                    upper = lower + 10000000000000
                return Q(raise_amount_received_online__gt=lower, raise_amount_received_online__lt=upper)

        # noinspection PyPep8Naming,PyCallingNonCallable,PyMethodParameters
        class TestCompany(Company):
            objects = CompanyQueryset.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        assert hasattr(TestCompany.objects, 'raised_between')
        assert hasattr(TestCompany.objects.all(), 'raised_between')

        class InvestmentQuerySet(QMethodQuerySet):
            def companies_raised_more_than(self, lower):
                return self.filter(company__qmatches=TestCompany.objects.raised_between.q(lower))

        class TestInvestment(Investment):
            objects = InvestmentQuerySet.as_manager()

            class Meta(object):
                proxy = True
                app_label = 'main'

        assert not hasattr(TestInvestment.objects, 'raised_between')
        assert not hasattr(TestInvestment.objects.all(), 'raised_between')
