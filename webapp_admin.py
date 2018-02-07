#!/usr/bin/env python
# Admin functions

import re
from functools import wraps
from flask import render_template, request, Response, Blueprint, jsonify, redirect
from config import config
import db
from webapp_base import pop_last_error, set_error
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
    models = db.get_models(details=True)
    return render_template('admin.html', num_images=num_images, num_human_annotations=num_human_annotations,
                           datasets=datasets, enqueued=enqueued, status=db.get_status('worker'), error=pop_last_error(),
                           models=models)

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


@admin.route('/admin/retrain', methods=['POST'])
@requires_admin
def admin_retrain():
    data = request.form
    model_name = data['train_model_name']
    # Race condition here; but it's just for the admin page anyway
    if re.match('^[\w-]+$', model_name) is None:
        set_error('Invalid model name. Must be non-empty, only alphanumeric characters, dashes and underscores.')
        return redirect('/admin')
    if db.get_model_by_name(model_name):
        set_error('Model exists. Please pick a different name.')
        return redirect('/admin')
    # Validate tag
    tag_name = data['train_label']
    dsets = list(db.get_datasets_by_tag(tag_name))
    if not len(dsets):
        set_error('Train tag does not match any datasets.')
        return redirect('/admin')
    is_primary = (data.get('train_primary') == 'on')
    train_sample_limit_s = data['train_sample_limit']
    if len(train_sample_limit_s):
        try:
            train_sample_limit = int(train_sample_limit_s)
            if train_sample_limit <= 0:
                raise ValueError()
        except ValueError as e:
            set_error('Invalid sample limit. Either leave empty for no limit, '
                      'or supply a valid number greater than zero.')
            return redirect('/admin')
    else:
        train_sample_limit = None
    # Add scheduled model training to DB. Will be picked up by worker.
    rec = db.add_model(model_name=model_name,
                       margin=96,
                       sample_limit=train_sample_limit,
                       train_tag=tag_name,
                       scheduled_primary=is_primary,
                       status=db.model_status_scheduled)
    set_error('Model training scheduled.')
    return redirect('/model/' + str(rec['_id']))

#    if os.path.isfile(retrain_log_filename):
#        log = open(retrain_log_filename, 'rt').read().strip()
#        log = filter(lambda x: x in string.printable, log)
#    else:
#        log = 'No logfile found.'
#    return render_template('model.html', log=log, error=pop_last_error())
