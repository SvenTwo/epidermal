#!/usr/bin/env python
# Datasets (of samples) functions

from flask import Blueprint, redirect, request, render_template
import db
from bson.objectid import ObjectId
from webapp_base import set_error, pop_last_error
from webapp_upload import upload_file
from webapp_users import get_current_user_id
from math import sqrt

datasets = Blueprint('datasets', __name__, template_folder='templates')

# Add dataset
@datasets.route('/add_dataset', methods=['POST'])
def add_dataset():
    # Add by name. Forward to newly created dataset
    dataset_name = request.form['dataset_name'].strip()
    if dataset_name == '':
        set_error('Invalid dataset name.')
        return redirect('/')
    dataset_info = db.get_dataset_by_name(dataset_name)
    if dataset_info is not None:
        set_error('Duplicate dataset name.')
        return redirect('/')
    dataset_info = db.add_dataset(dataset_name, user_id=get_current_user_id())
    return redirect('/dataset/' + str(dataset_info['_id']) + '?new=true')


# Delete dataset
@datasets.route('/delete_dataset/<dataset_id_str>', methods=['POST'])
def delete_dataset(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    if dataset_info is None:
        return render_template("404.html")
    if db.is_readonly_dataset(dataset_info):
        set_error('Dataset is protected.')
        return redirect('/dataset/' + str(dataset_info['_id']))
    db.delete_dataset(dataset_id)
    set_error('Dataset "%s" deleted.' % dataset_info['name'])
    return redirect('/')

# Main overview page within a dataset
@datasets.route('/dataset/<dataset_id_str>', methods=['GET', 'POST'])
def dataset_info(dataset_id_str):
    print 'request.method', request.method
    if dataset_id_str == 'new' and request.method == 'POST':
        dataset_id = None
        dataset_info = None
    else:
        dataset_id = ObjectId(dataset_id_str)
        dataset_info = db.get_dataset_by_id(dataset_id)
        if dataset_info is None:
            return render_template("404.html")
    if request.method == 'POST':
        # File upload
        if dataset_info is not None:
            if db.is_readonly_dataset(dataset_info):
                set_error('Dataset is protected.')
                return redirect('/dataset/' + dataset_id_str)
        return upload_file(dataset_id)
    enqueued = db.get_unprocessed_samples(dataset_id=dataset_id)
    finished = db.get_processed_samples(dataset_id=dataset_id)
    for i, sample in enumerate(finished):
        sample['machine_distance'] = 1.0/max([0.001, sqrt(float(sample['machine_position_count']))])
        sample['index'] = i
    errored = db.get_error_samples(dataset_id=dataset_id)
    # Get request data
    return render_template("dataset.html", dataset_name=dataset_info['name'], dataset_id=dataset_id_str,
                           enqueued=enqueued, finished=finished, errored=errored, status=db.get_status('worker'),
                           readonly=db.is_readonly_dataset(dataset_info), error=pop_last_error(),
                           dataset_user=dataset_info.get('user'))

