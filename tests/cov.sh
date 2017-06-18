#!/bin/sh
venv/bin/coverage run --branch --include="*cabinet*" --omit="*tests*" ./manage.py test -v 2 testapp
venv/bin/coverage html
