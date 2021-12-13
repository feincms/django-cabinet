VERSION = (0, 11, 6)
__version__ = ".".join(map(str, VERSION))

try:
    import django
except ModuleNotFoundError:
    pass
else:
    if django.VERSION < (3, 2):
        default_app_config = "cabinet.apps.CabinetConfig"
