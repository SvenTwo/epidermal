#!/usr/bin/env python
# Basic functions for stomata web server

from flask import request, redirect, Blueprint, render_template, send_from_directory

from stoma_counter_peaks import default_prob_threshold
from apply_fcn_caffe import fc8_to_prob
from config import config


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
@base.route('/disclaimer')
def disclaimer():
    return render_template("disclaimer.html", error=pop_last_error())


# Source code page
@base.route('/source')
def source_redirect():
    return redirect("https://github.com/SvenTwo/epidermal")


# Upload page
@base.route('/upload')
def upload():
    threshold_prob = fc8_to_prob(default_prob_threshold)
    return render_template("upload.html", error=pop_last_error(), threshold_prob=threshold_prob,
                           threshold_prob_short=round(threshold_prob, ndigits=3))


# Loading... page
@base.route('/loading/<path:target_path>')
def loading_page(target_path):
    target_desc = ''
    if 'export_err_by_threshold' in target_path:
        target_desc = 'Error by threshold graph'
    elif 'export_correlation' in target_path:
        target_desc = 'Human-to-automatic stomata count correlation'
    return render_template("loading.html", error=pop_last_error(), target_path=target_path, target_desc=target_desc)


# Static images/heatmaps
@base.route('/static/images/images/<path:path>')
def static_images(path):
    return send_from_directory(config.get_server_image_path(), path)


@base.route('/static/images/heatmaps/<path:path>')
def static_heatmaps(path):
    return send_from_directory(config.get_server_heatmap_path(), path)
