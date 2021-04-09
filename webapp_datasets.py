#!/usr/bin/env python
# Datasets (of samples) functions

from flask import Blueprint, redirect, request, render_template
from math import sqrt
from bson.objectid import ObjectId

from webapp_base import set_error, pop_last_error, set_notice
from webapp_upload import upload_file
from webapp_users import get_current_user_id
import db
from stoma_counter_peaks import default_prob_threshold
from apply_fcn_caffe import prob_to_fc8, fc8_to_prob


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
    db.delete_dataset(dataset_id, recycle=False, delete_files=True)
    set_notice('Dataset "%s" deleted.' % dataset_info['name'])
    return redirect('/')


@datasets.route('/dataset/<dataset_id_str>/rerun')
def dataset_rerun(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    count = db.remove_machine_annotations_for_dataset(dataset_id)
    set_notice('%d annotations removed.' % count)
    return redirect('/dataset/' + dataset_id_str)


@datasets.route('/dataset/<dataset_id_str>/set_threshold/<new_threshold_str>')
def dataset_set_threshold(dataset_id_str, new_threshold_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    new_threshold = float(new_threshold_str)
    if dataset_info.get('threshold_prob') == new_threshold:
        set_notice('Threshold not updated: Values are identical.')
    else:
        db.set_dataset_threshold_prob(dataset_id, new_threshold)
        count = db.remove_machine_annotations_for_dataset(dataset_id)
        set_notice('Threshold updated. %d annotations removed.' % count)
    return redirect('/dataset/' + dataset_id_str)


# Main overview page within a dataset
@datasets.route('/dataset/<dataset_id_str>', methods=['GET', 'POST'])
def dataset_info(dataset_id_str):
    print 'request.method', request.method
    new_dataset_threshold_prob = None
    new_allow_reuse = False
    if dataset_id_str == 'new':
        print 'Creating new dataset'
        if request.method != 'POST':
            return redirect('/')
        dataset_id = None
        dataset_info = None
        new_dataset_zoom = request.form['size']
        print 'Threshold prob:'
        print request.form['threshold']
        try:
            v = float(request.form['threshold'])
            new_dataset_threshold_prob = min(max(v, 0.5), 1.0)
            print 'Specified thresh prob:', new_dataset_threshold_prob
        except ValueError:
            print 'Invalid threshold. Ignored.'
        try:
            new_allow_reuse = bool(request.form.get('reuseCheck'))
            print 'Specified allow reuse:', request.form.get('reuseCheck'), new_allow_reuse
        except ValueError:
            print 'Invalid reuse setting. Ignored.'
    else:
        dataset_id = ObjectId(dataset_id_str)
        db.access_dataset(dataset_id)
        dataset_info = db.get_dataset_by_id(dataset_id)
        new_dataset_zoom = None
        if dataset_info is None:
            return render_template("404.html")
    if request.method == 'POST':
        # File upload
        if dataset_info is not None:
            if db.is_readonly_dataset(dataset_info):
                set_error('Dataset is protected.')
                return redirect('/dataset/' + dataset_id_str)
        return upload_file(dataset_id, image_zoom=new_dataset_zoom, threshold_prob=new_dataset_threshold_prob,
                           allow_reuse=new_allow_reuse)
    enqueued = db.get_unprocessed_samples(dataset_id=dataset_id)
    finished = db.get_processed_samples(dataset_id=dataset_id)
    for i, sample in enumerate(finished):
        sample['machine_distance'] = 1.0/max([0.001, sqrt(float(sample['machine_position_count']))])
        sample['index'] = i
    errored = db.get_error_samples(dataset_id=dataset_id)
    threshold_prob = round(dataset_info.get('threshold_prob') or fc8_to_prob(default_prob_threshold), ndigits=3)
    # Get request data
    return render_template("dataset.html", dataset_name=dataset_info['name'], dataset_id=dataset_id_str,
                           enqueued=enqueued, finished=finished, errored=errored, status=db.get_status('worker'),
                           readonly=db.is_readonly_dataset(dataset_info), error=pop_last_error(),
                           dataset_user=dataset_info.get('user'), image_zoom=dataset_info.get('image_zoom', 'default'),
                           threshold_prob=threshold_prob)

