# coding=utf-8

from django.db.models.query_utils import Q
from django.utils import timezone

from main.models import MiscModel
from .base import QInPythonTestCase


class TestLookups(QInPythonTestCase):
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
        MiscModel(text='hello', foreign=related).save()
        MiscModel(text='hola', foreign=related).save()

        q = Q(miscmodel__text='hello')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel__text='adios')
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel__text='hola')
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

        q = Q(miscmodel__miscmodel__miscmodel__miscmodel__foreign__foreign__integer=2)
        self.assertEqual(1, MiscModel.objects.filter(q).count())
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)

        q = Q(miscmodel__miscmodel__miscmodel__miscmodel__foreign__integer=9)
        self.assert_q_executes_the_same_in_python_and_sql(MiscModel, q)
