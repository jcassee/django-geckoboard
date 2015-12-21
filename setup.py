from setuptools import setup, Command
import os

import django_geckoboard


os.environ['DJANGO_SETTINGS_MODULE'] = 'django_geckoboard.tests.settings'


cmdclass = {}


class TestCommand(Command):
    description = "run package tests"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from django_geckoboard.tests.utils import run_tests
        run_tests()

cmdclass['test'] = TestCommand


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def build_long_description():
    return "\n\n".join([
        django_geckoboard.__doc__,
        read('CHANGELOG.rst'),
    ])


setup(
    name='django-geckoboard',
    version=django_geckoboard.__version__,
    license=django_geckoboard.__license__,
    description='Geckoboard custom widgets for Django projects',
    long_description=build_long_description(),
    author=django_geckoboard.__author__,
    author_email=django_geckoboard.__email__,
    packages=[
        'django_geckoboard',
        'django_geckoboard.tests',
    ],
    install_requires=['six', 'django'],
    extras_require={
        'encryption': ['pycrypto']
    },
    keywords=['django', 'geckoboard'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    platforms=['any'],
    url='http://github.com/jcassee/django-geckoboard',
    download_url='http://github.com/jcassee/django-geckoboard/archives/master',
    cmdclass=cmdclass,
)
