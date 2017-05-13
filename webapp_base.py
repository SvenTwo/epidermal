#!/usr/bin/env python
# Basic functions for stomata web server

from flask import request, redirect, Blueprint

base = Blueprint('base', __name__, template_folder='templates')

# Error handling
base.epi_last_error = None
def set_error(msg): base.epi_last_error = msg
def error_redirect(msg):
    set_error(msg)
    return redirect(request.url)
def pop_last_error():
    last_error = base.epi_last_error
    base.epi_last_error = None
    return last_error
