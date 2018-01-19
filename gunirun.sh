#!/usr/bin/env bash

gunicorn --timeout 1200 --workers 3 --bind 0.0.0.0:8000 wsgi
