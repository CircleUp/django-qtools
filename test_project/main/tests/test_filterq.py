# coding=utf-8

from django.db.models.query_utils import Q
from django.test.testcases import TestCase
from django.utils import timezone
from qtools.filterq import filter_by_q

from main.models import MiscModel, Order, Pizza
from .base import QInPythonTestCaseMixin


class TestFilteringOverRelationships(TestCase, QInPythonTestCaseMixin):
    def test_example(self):
        order = Order(price=100, name_on_order='Bob')
        order.save()

        pizza = Pizza(diameter=12, order=order, created=timezone.now())
        pizza.save()

        self.assertEqual(0, Pizza.objects.is_delivered().count())
        self.assertEqual(0, Order.objects.is_delivered().count())
        self.assertFalse(pizza.is_delivered)

        order.delivered_time = timezone.now()
        order.save()

        self.assertEqual(1, Order.objects.is_delivered().count())
        self.assertEqual(1, Pizza.objects.is_delivered().count())
        self.assertTrue(pizza.is_delivered)

    def test_everything_together(self):
        m1 = MiscModel(text='hello', integer=5)
        m1.save()

        m2 = MiscModel(text='goodbye', integer=50)
        m2.save()

        m3 = MiscModel(text='howdy', datetime=timezone.now())
        m3.save()

        m1.foreign = m2
        m2.foreign = m3
        m3.foreign = m1

        m1.save()
        m2.save()
        m3.save()

        q = Q(text='hola') | (Q(integer__gt=49) & Q(text='goodbye') & Q(integer__lt=500)) | Q(text__lt='zzzzzzzzzzzzz', miscmodel__miscmodel__miscmodel__miscmodel__foreign__foreign__integer=5)
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

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

    def test_related_object(self):
        MiscModel().save()

        related = MiscModel(text='goodbye')
        related.save()

        main = MiscModel(text='hello', foreign=related)
        main.save()

        q = Q(foreign__text='goodbye')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

    def test_related_object_reverse_relation(self):
        MiscModel().save()
        related = MiscModel(text='goodbye').save()
        hello_model = MiscModel(text='hello', foreign=related)
        hello_model.save()
        MiscModel(text='hola', foreign=related).save()

        q = Q(miscmodel__text='hello')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel__text='adios')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel__text='hola')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel=hello_model)
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

    def test_several_degree_related_object(self):
        m1 = MiscModel(integer=1)
        m2 = MiscModel(integer=2)
        m3 = MiscModel(integer=3)

        m1.save()
        m2.save()
        m3.save()

        m1.foreign = m2
        m2.foreign = m3
        m3.foreign = m1

        m1.save()
        m2.save()
        m3.save()

        q = Q(miscmodel__miscmodel__miscmodel__foreign__foreign__integer=2)
        self.assertEqual(1, MiscModel.objects.filter(q).count())
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel__miscmodel__miscmodel__foreign__integer=9)
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

    def test_one_to_one_related_object(self):
        m1 = MiscModel(integer=1)
        m1.save()

        m2 = MiscModel(integer=2, main_info=m1)
        m2.save()

        q_to_test = [
            Q(extra_info=m2),
            Q(extra_info=m1),
            Q(main_info=m1),
            Q(main_info=m2)
        ]
        all_models = list(MiscModel.objects.all())
        for q in q_to_test:
            filter_by_q(all_models, q)
            self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)
