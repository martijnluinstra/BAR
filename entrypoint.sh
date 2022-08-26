#!/usr/bin/env bash
flask db upgrade
uwsgi --ini uwsgi.ini
