"""
django-geckoboard testing settings.
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django_geckoboard',
]
GECKOBOARD_PASSWORD = b'pass123'

SECRET_KEY = b'test'
