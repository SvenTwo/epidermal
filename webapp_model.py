#!/usr/bin/env python
# Model overview and functions

import os
from flask import render_template, Blueprint, redirect, send_from_directory
import db
from bson.objectid import ObjectId
import re

from webapp_base import pop_last_error, set_notice
from webapp_admin import requires_admin
from config import config


bp_model = Blueprint('model', __name__, template_folder='templates')


def enqueue_images_for_model(model_id):
    undeleted_dataset_ids = set([ds['_id'] for ds in db.get_datasets()])
    # Find all images not processed by the given model
    all_sample_ids = set([s['_id'] for s in db.get_samples() if s['dataset_id'] in undeleted_dataset_ids])
    machine_annotations = set([a['sample_id'] for a in db.get_machine_annotations_for_model(model_id=model_id)])
    enqueued_samples = set([s['sample_id'] for s in db.get_queued_samples(model_id=model_id) if 'sample_id' in s])
    sample_ids_to_enqueue = all_sample_ids - machine_annotations - enqueued_samples
    for sample_id in sample_ids_to_enqueue:
        db.queue_sample(sample_id=sample_id, model_id=model_id)
    return len(sample_ids_to_enqueue)


@bp_model.route('/enqueue_images/<model_id_s>')
@requires_admin
def enqueue_images(model_id_s):
    model_id = ObjectId(model_id_s)
    n = enqueue_images_for_model(model_id)
    set_notice('Enqueued %d images.' % n)
    return redirect('/model/' + model_id_s)


@bp_model.route('/enqueue_all_images')
@requires_admin
def enqueue_all_images():
    n = 0
    m = 0
    for model in db.get_models(details=False, status=db.model_status_trained):
        if not model['primary']:
            nm = enqueue_images_for_model(model['_id'])
            if nm:
                n += nm
                m += 1
    set_notice('Enqueued %d images from %d models.' % (n, m))
    return redirect('/admin')


def enqueue_validation_sets_for_model(train_model_id):
    existing_results = db.get_all_validation_results(train_model_id=train_model_id)
    processed_val_model_ids = set([r['validation_model_id'] for r in existing_results if r['image_subset'] == 'train'])
    n = 0
    for validation_model in db.get_models(details=False, status=db.model_status_trained):
        if validation_model['_id'] not in processed_val_model_ids:
            db.queue_validation(train_model_id=train_model_id, validation_model_id=validation_model['_id'])
            n += 1
    return n


@bp_model.route('/enqueue_validation_sets/<model_id_s>')
@requires_admin
def enqueue_validation_sets(model_id_s):
    model_id = ObjectId(model_id_s)
    n = enqueue_validation_sets_for_model(model_id)
    set_notice('Enqueued %d sets.' % n)
    return redirect('/model/' + model_id_s)


@bp_model.route('/enqueue_all_validation_sets')
@requires_admin
def enqueue_all_validation_sets():
    n = 0
    m = 0
    for model in db.get_models(details=False, status=db.model_status_trained):
        nm = enqueue_validation_sets_for_model(model['_id'])
        if nm:
            n += nm
            m += 1
    set_notice('Enqueued %d sets from %d models.' % (n, m))
    return redirect('/admin')


@bp_model.route('/model/<model_id_s>')
@requires_admin
def model_page(model_id_s):
    model_id = ObjectId(model_id_s)
    model = dict(db.get_model_by_id(model_id))
    model_data = [(k, v) for k, v in sorted(model.iteritems())]
    exec_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cnn'))
    exec_path = os.path.join(exec_base_path, str(model_id))
    log_filename = os.path.join(exec_path, 'train.log')
    if os.path.isfile(log_filename):
        log_data = open(log_filename, 'rt').read()
    else:
        log_data = 'logfile not found: %s' % log_filename
    # Get validation results by model
    validation_results = db.get_all_validation_results(train_model_id=model_id)
    for vr in validation_results:
        vr['image_set'] = '(%s) %s' % (vr['image_subset'], db.get_model_by_id(vr['validation_model_id'])['name'])
        cm = vr['confusion_matrix']
        vr['accuracy'] = '%.1f' % (100.0 * (cm[0][0] + cm[1][1]) / (cm[0][0] + cm[1][1] + cm[1][0] + cm[0][1]))
    validation_results = sorted(validation_results, key=lambda f: f['image_set'])
    # Get validation results by dataset
    validation_results_ds = db.get_all_validation_results(validation_model_id=model_id)
    for vr in validation_results_ds:
        vr['model_name'] = '(%s) %s' % (vr['image_subset'], db.get_model_by_id(vr['train_model_id'])['name'])
        cm = vr['confusion_matrix']
        vr['accuracy'] = '%.1f' % (100.0 * (cm[0][0] + cm[1][1]) / (cm[0][0] + cm[1][1] + cm[1][0] + cm[0][1]))
    validation_results_ds = sorted(validation_results_ds, key=lambda f: f['model_name'])
    return render_template('model.html', model_id=model_id_s, name=model['name'], model_data=model_data, log=log_data,
                           validation_results=validation_results, validation_results_ds=validation_results_ds,
                           error=pop_last_error())


@bp_model.route('/validation/<val_id_s>')
@requires_admin
def validation_page(val_id_s):
    val_id = ObjectId(val_id_s)
    val = dict(db.get_validation_results_by_id(val_id))
    train_model = db.get_model_by_id(val['train_model_id'])
    val_model = db.get_model_by_id(val['validation_model_id'])
    train_name = train_model['name']
    val_name = '%s (%s)' % (val_model['name'], val['image_subset'])
    worst_predictions = val['worst_predictions']
    return render_template('validation.html', train_id=val['train_model_id'], train_name=train_name, val_name=val_name,
                           worst_predictions=worst_predictions, error=pop_last_error())


@bp_model.route('/image_sample/<train_id_s>/<path:sample_name>')
@requires_admin
def image_sample(train_id_s, sample_name):
    subpath = os.path.join(train_id_s, 'samples', sample_name)
    return send_from_directory(config.train_data_path, subpath)
