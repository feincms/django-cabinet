import django

VERSION = (0, 11, 5)
__version__ = ".".join(map(str, VERSION))

if django.VERSION < (3, 2):
    default_app_config = "cabinet.apps.CabinetConfig"
