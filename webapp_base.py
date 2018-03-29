#!/usr/bin/env python
# Basic functions for stomata web server

from flask import request, redirect, Blueprint, render_template

base = Blueprint('base', __name__, template_folder='templates')

# Errors and notices handling
base.epi_last_messages = []


def set_error(msg):
    base.epi_last_messages.append(('Error', msg, 'danger'))


def set_notice(msg):
    base.epi_last_messages.append(('Notice', msg, 'info'))


def error_redirect(msg):
    set_error(msg)
    return redirect(request.url)


def pop_last_error():
    last_messages = base.epi_last_messages
    base.epi_last_messages = []
    return last_messages


# Main page
@base.route('/')
def overview():
    return render_template("index.html", error=pop_last_error())


# Info page
@base.route('/about')
def about():
    return render_template("about.html", error=pop_last_error())


# Info page
@base.route('/source')
def source_redirect():
    return redirect("https://github.com/SvenTwo/epidermal")
