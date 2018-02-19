#!/usr/bin/env python
# Model overview and functions

import os
from flask import render_template, Blueprint, redirect
import db
from webapp_base import pop_last_error, set_notice
from webapp_admin import requires_admin
from bson.objectid import ObjectId


bp_model = Blueprint('model', __name__, template_folder='templates')


def enqueue_images_for_model(model_id):
    undeleted_dataset_ids = set([ds['_id'] for ds in db.get_datasets()])
    # Find all images not processed by the given model
    all_sample_ids = set([s['_id'] for s in db.get_samples() if s['dataset_id'] in undeleted_dataset_ids])
    machine_annotations = set([a['sample_id'] for a in db.get_machine_annotations_for_model(model_id=model_id)])
    enqueued_samples = set([s['sample_id'] for s in db.get_queued_samples(model_id=model_id)])
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
    return render_template('model.html', model_id=model_id_s, name=model['name'], model_data=model_data, log=log_data,
                           error=pop_last_error())
