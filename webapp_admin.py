#!/usr/bin/env python
# Admin functions

import os
import re
from datetime import datetime
from functools import wraps
from flask import render_template, request, Response, Blueprint, jsonify, redirect
from bson.objectid import ObjectId
import subprocess

from config import config
import db
from cleanup_old_datasets import find_old_datasets, delete_datasets
from webapp_base import pop_last_error, set_error, set_notice

admin = Blueprint('admin', __name__, template_folder='templates')


def bytes_humanfriendly(n_bytes):
    suffixes = ('%d bytes', '%1.2f kb', '%1.2f MB', '%1.2f GB', '%1.2f TB', '%1.2f PB', '%1.2f ExB')
    for suffix in suffixes:
        if n_bytes < 1024 or suffix == suffixes[-1]:
            return suffix % n_bytes
        n_bytes = float(n_bytes) / 1024


def get_recursive_folder_size(path):
    size = int(subprocess.check_output(['du', '-sb', path]).split()[0].decode('utf-8'))
    return size


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


status_ids = (
    ('Count worker', 'worker'),
    ('Validation worker', 'sec_worker'),
    ('Network trainer', 'trainer'),
)


@admin.route('/admin')
def admin_overview():
    return render_template('admin.html', error=pop_last_error())


@admin.route('/admin/datasets')
@requires_admin
def admin_datasets():
    datasets = db.get_datasets()
    for dataset in datasets:
        if dataset.get('date_accessed') is None:
            dataset['date_accessed'] = datetime.now()
            db.access_dataset(dataset['_id'])
    return render_template('admin_datasets.html', datasets=datasets, error=pop_last_error())


@admin.route('/admin/models')
@requires_admin
def admin_models():
    models = db.get_models(details=True)
    return render_template('admin_models.html', models=models, error=pop_last_error())


@admin.route('/admin/storage')
@requires_admin
def admin_storage():
    num_images = db.get_sample_count()
    num_human_annotations = db.get_human_annotation_count()
    paths = (
        ('server_heatmap', config.get_server_heatmap_path()),
        ('server_image', config.get_server_image_path()),
        ('cnn', config.get_cnn_path()),
        ('caffe', config.get_caffe_path()),
        ('plot', config.get_plot_path()),
        ('train_data', config.get_train_data_path()),
    )
    path_data = []
    for path_name, path in paths:
        pstats = os.statvfs(path)
        path_data.append({
            'name': path_name,
            'path': path,
            'disk_total': bytes_humanfriendly(pstats.f_frsize * pstats.f_blocks),
            'disk_avail': bytes_humanfriendly(pstats.f_frsize * pstats.f_bavail),
            'used': bytes_humanfriendly(get_recursive_folder_size(path)) if path_name != 'train_data' else '?'
        })
    return render_template('admin_storage.html', num_images=num_images, num_human_annotations=num_human_annotations,
                           path_data=path_data, error=pop_last_error())


@admin.route('/admin/worker')
@requires_admin
def admin_worker():
    enqueued = db.get_unprocessed_samples()
    models = db.get_models(details=True)
    model_id_to_name = {m['_id']: m['name'] for m in models}
    secondary_items = db.get_queued_samples()
    enqueued2 = []
    for item in secondary_items:
        model_name = model_id_to_name.get(item['model_id'], '???')
        if 'sample_id' in item:
            target_name = db.get_sample_by_id(item['sample_id'])['filename']
        elif 'validation_model_id' in item:
            target_name = model_id_to_name.get(item['validation_model_id'], '?!?')
        else:
            target_name = '!!!'
        enqueued2.append((model_name, target_name, str(item['_id'])))
    enqueued2 = sorted(enqueued2, key=lambda item: item[0])
    status = [(status_name, db.get_status(status_id)) for status_name, status_id in status_ids]
    return render_template('admin_worker.html', enqueued=enqueued, status=status, enqueued2=enqueued2, error=pop_last_error())


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


@admin.route('/unqueue/<queue_id_s>', methods=['POST'])
@requires_admin
def unqueue_validation(queue_id_s):
    queue_id = ObjectId(queue_id_s)
    db.unqueue_sample(queue_id)
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
    dataset_only = (data.get('dataset_only') == 'on')
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
                       status=db.model_status_scheduled,
                       dataset_only=dataset_only)
    set_notice('Model training scheduled.')
    return redirect('/model/' + str(rec['_id']))


@admin.route('/admin/delete_expired_datasets')
@requires_admin
def delete_expired_datasets():
    ds = find_old_datasets()
    delete_datasets(ds)
    set_notice('%d datasets deleted' % len(ds))
    return redirect('/admin')
