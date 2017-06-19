#!/bin/sh
venv/bin/coverage run --branch --include="*cabinet*" --omit="*migrations*,*tests*" ./manage.py test -v 2 testapp
venv/bin/coverage html
