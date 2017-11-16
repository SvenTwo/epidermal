#!/usr/bin/env python
# Basic functions for stomata web server

from flask import request, redirect, Blueprint, render_template

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


# Main page
@base.route('/')
def overview():
    return render_template("index.html", error=pop_last_error())


# Info page
@base.route('/about')
def about(): return render_template("about.html", error=pop_last_error())
