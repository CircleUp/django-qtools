from distutils.core import setup

long_description = """
Standard Django forces business logic to be repeated as it's used in different contexts (querying, instance methods,
querying related objects).  This repetition makes is hard to maintain and definitions frequently become out of sync.
This library allows a piece of filtering logic to be written once and then used in many different contexts.
"""

setup(
    name='django-qtools',
    version='1.0',
    author='CircleUp, Bryce Drennan',
    author_email='bdrennan@circleup.com',
    url='https://github.com/CircleUp/django-qtools',
    download_url='https://github.com/CircleUp/django-qtools/tarball/1.0',
    keywords=['queryset', 'query', 'filtering', 'django'],
    packages=['qtools'],
    license='MIT',
    description='Write DRY, composable filtering logic for data queries and instance methods.',
    long_description=long_description,
)
