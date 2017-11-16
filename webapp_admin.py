#!/usr/bin/env python
# Admin functions

import os
from functools import wraps
from flask import render_template, request, Response, Blueprint, jsonify
from config import config
import db
#from retrain_network import is_network_retrain_running, launch_network_retrain, retrain_log_filename
import string
from webapp_base import pop_last_error
from bson.objectid import ObjectId

admin = Blueprint('admin', __name__, template_folder='templates')

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == config.admin_username and password == config.admin_password

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@admin.route('/admin')
@requires_admin
def admin_page():
    num_images = db.get_sample_count()
    num_human_annotations = db.get_human_annotation_count()
    datasets = db.get_datasets()
    enqueued = db.get_unprocessed_samples()
    return render_template('admin.html', num_images=num_images, num_human_annotations=num_human_annotations,
                           datasets=datasets, enqueued=enqueued, status=db.get_status('worker'), error=pop_last_error())

@admin.route('/tag/add', methods=['POST'])
@requires_admin
def tag_add():
    data = request.form
    dataset_id = ObjectId(data['dataset_id'])
    new_tag_name = data['tag_name']
    db.add_dataset_tag(dataset_id, new_tag_name)
    print 'Added tag %s to %s' % (new_tag_name, dataset_id)
    return jsonify('OK'), 200


@admin.route('/tag/remove', methods=['POST'])
@requires_admin
def tag_remove():
    data = request.form
    dataset_id = ObjectId(data['dataset_id'])
    tag_name = data['tag_name']
    db.remove_dataset_tag(dataset_id, tag_name)
    print 'Removed tag %s from %s' % (tag_name, dataset_id)
    return jsonify('OK'), 200


@admin.route('/admin/retrain', methods=['GET', 'POST'])
@requires_admin
def admin_retrain():
#    if request.method == 'POST':
#        if not is_network_retrain_running():
#            launch_network_retrain()
#    if os.path.isfile(retrain_log_filename):
#        log = open(retrain_log_filename, 'rt').read().strip()
#        log = filter(lambda x: x in string.printable, log)
#    else:
#        log = 'No logfile found.'
#    return render_template('admin_retrain.html', log=log, error=pop_last_error())
    return render_template('admin_retrain.html', log='Not implemented', error=pop_last_error())
