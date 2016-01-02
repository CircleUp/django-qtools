from __future__ import unicode_literals

from django.db import models
from django.test.testcases import TestCase
from django.utils import timezone

from main.models import Order, Pizza, OrderQuerySet
from qtools import nested_q


class QMethodDecoratorTests(TestCase):

    def test_q_method_cant_use_self(self):
        order = Order(price=100)
        order.save()

        pizza = Pizza(diameter=12, order=order, created=timezone.now())
        pizza.save()

        with self.assertRaisesRegexp(Exception, 'q_method'):
            Pizza.objects.is_delivered_using_self()

    def test_q_method_with_args(self):
        """Test whether q method can handle args and kwargs"""
        amount = 100
        order = Order(price=amount)
        order.save()

        # test various combinations of args and kwargs on the manager method
        self.assertEqual(1, Order.objects.cost_between(amount - 1).count())
        self.assertEqual(1, Order.objects.cost_between(amount - 1, amount + 1).count())
        self.assertEqual(1, Order.objects.cost_between(amount - 1, upper=amount + 1).count())
        self.assertEqual(1, Order.objects.cost_between(lower=amount - 1, upper=amount + 1).count())
        self.assertEqual(0, Order.objects.cost_between(amount + 1).count())
        self.assertEqual(0, Order.objects.cost_between(lower=amount + 1, upper=amount + 2).count())

        # test various combinations of args and kwargs on the queryset method
        self.assertEqual(1, Order.objects.all().cost_between(amount - 1).count())
        self.assertEqual(1, Order.objects.all().cost_between(amount - 1, amount + 1).count())
        self.assertEqual(1, Order.objects.all().cost_between(amount - 1, upper=amount + 1).count())
        self.assertEqual(1, Order.objects.all().cost_between(lower=amount - 1, upper=amount + 1).count())
        self.assertEqual(0, Order.objects.all().cost_between(amount + 1).count())
        self.assertEqual(0, Order.objects.all().cost_between(lower=amount + 1, upper=amount + 2).count())

    def test_q_method_used_from_other_model(self):
        """
        Use a @q_method from a different model in a queryset

        This test is a good example of a plausible use case for this.
        """

        order = Order(price=100)
        order.save()

        pizza = Pizza(diameter=12, order=order, created=timezone.now())
        pizza.save()

        self.assertEqual(0, Pizza.objects.is_delivered().count())

        order.delivered_time = timezone.now()
        order.save()

        self.assertEqual(1, Pizza.objects.is_delivered().count())

    def test_valid_api_works(self):
        Order(price=100).save()

        # valid api
        self.assertIsInstance(Order.objects.cost_between(lower=50), models.QuerySet)
        self.assertIsInstance(OrderQuerySet.cost_between.q(lower=50), models.Q)
        q1 = OrderQuerySet.cost_between.q(lower=50)
        q2 = OrderQuerySet.cost_between.q(upper=200000)
        Pizza.objects.filter(nested_q('order', q1 & q2))

        # invalid api
        with self.assertRaisesRegexp(Exception, 'Not a Q object'):
            Pizza.objects.filter(nested_q('order', Order.objects.cost_between(0, 500)))

        # invalid api
        with self.assertRaisesRegexp(AttributeError, 'no attribute'):
            q2 = Order.objects.cost_between.q(upper=200000)

    def test_q_methods_do_not_leak_across_instances(self):
        """
        @q_methods should only be available on the queryset that has them defined.

        They should not be added at the class level or they'll leak between models.
        This was a horrible bug that took forever to debug.
        """
        assert hasattr(Order.objects, 'cost_between')  # on manager
        assert hasattr(Order.objects.all(), 'cost_between')  # on queryset
        assert not hasattr(Pizza.objects, 'cost_between')  # on manager
        assert not hasattr(Pizza.objects.all(), 'cost_between')  # on queryset
