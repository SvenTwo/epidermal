#!/usr/bin/env python
# Export-to-csv functionality

import os
from functools import wraps
from bson.objectid import ObjectId
from flask import render_template, request, Response, Blueprint
from config import config
import db
#from retrain_network import is_network_retrain_running, launch_network_retrain, retrain_log_filename
import string
from webapp_base import pop_last_error
from webapp_admin import requires_admin
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from math import sqrt
from itertools import chain

from webapp_samples import info_table_entries
from webapp_users import get_current_user_id
from evaluation.eval_threshold import plot_err_by_threshold
from webapp_plots import get_plot_as_png


data_export = Blueprint('data_export', __name__, template_folder='templates')


export_fields = (
    ('Name', 'name'),
    ('Status', 'status'),
    ('Dataset', 'dataset_name'),
    ('Manual_count', 'human_position_count'),
    ('Automatic_count', 'machine_position_count'),
    ('Human distance', 'human_distance'),
    ('Machine distance', 'machine_distance'),
    ('Machine hopkins', 'machine_hopkins')) + info_table_entries
export_names = [e[0] for e in export_fields]
export_keys = [e[1] for e in export_fields]


def export_generator(samples, yield_header=True):
    if yield_header:
        yield ','.join(export_names) + '\n'
    for s in samples:
        if s.get('machine_position_count'):
            s['machine_distance'] = 1.0 / sqrt(float(s['machine_position_count']))
        if s.get('human_position_count'):
            s['human_distance'] = 1.0 / sqrt(float(s['human_position_count']))
        if s['error']:
            status = 'ERROR'
        elif not s['processed']:
            status = 'QUEUED'
        else:
            status = 'OK'
        s['status'] = status
        yield ','.join([str(s.get(k)) for k in export_keys]) + '\n'


def export_positions_generator(samples, yield_header=True, human=False):
    if yield_header:
        yield ','.join(('sample_name', 'sample_filename',
                        'center_x_px', 'center_y_px',
                        'center_x_relative', 'center_y_relatrive')) + '\n'
    for s in samples:
        sample_name = s.get('name')
        sample_filename = s.get('filename')
        if human:
            annotations = db.get_human_annotations(s['_id'])
        else:
            annotations = db.get_machine_annotations(s['_id'])
        if not annotations:
            continue
        size = s['size']
        for pos in annotations[0]['positions']:
            if human:
                pos = (pos['x'], pos['y'])
            rel_pos = ['%.3f' % (float(p) / s) for p, s in zip(pos, size)]
            yield ','.join(map(str, (sample_name, sample_filename, pos[0], pos[1], rel_pos[0], rel_pos[1]))) + '\n'


def get_all_samples(dataset_id, dataset_info=None):
    # Get all samples, annotated with dataset name
    if dataset_info is None:
        dataset_info = db.get_dataset_by_id(dataset_id)
    enqueued = db.get_unprocessed_samples(dataset_id=dataset_id)
    finished = db.get_processed_samples(dataset_id=dataset_id)
    errored = db.get_error_samples(dataset_id=dataset_id)
    all_samples = enqueued + finished + errored
    for s in all_samples:
        s['dataset_name'] = dataset_info.get('name')
    return all_samples


@data_export.route('/dataset/<dataset_id_str>/export')
def dataset_export(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    results = export_generator(get_all_samples(dataset_id, dataset_info))
    dataset_export_name, _ext = os.path.splitext(secure_filename(dataset_info['name']))
    dataset_export_name += '.csv'
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition":
                                 "attachment;filename=%s" % dataset_export_name})


@data_export.route('/dataset/<dataset_id_str>/export_human_positions')
def dataset_export_human_positions(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    results = export_positions_generator(get_all_samples(dataset_id, dataset_info), human=True)
    dataset_export_name, _ext = os.path.splitext(secure_filename(dataset_info['name'] + '_human_positions'))
    dataset_export_name += '.csv'
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition":
                                 "attachment;filename=%s" % dataset_export_name})


@data_export.route('/dataset/<dataset_id_str>/export_machine_positions')
def dataset_export_machine_positions(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    results = export_positions_generator(get_all_samples(dataset_id, dataset_info), human=False)
    dataset_export_name, _ext = os.path.splitext(secure_filename(dataset_info['name'] + '_machine_positions'))
    dataset_export_name += '.csv'
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition":
                                 "attachment;filename=%s" % dataset_export_name})


@data_export.route('/dataset/<dataset_id_str>/export_correlation')
def dataset_export_correlation(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    finished = db.get_processed_samples(dataset_id=dataset_id)
    valid = [s for s in finished if s.get('human_position_count') is not None and s.get('machine_position_count') is not None]
    hu = np.array([s['human_position_count'] for s in valid])
    ma = np.array([s['machine_position_count'] for s in valid])
    sns.jointplot(y=hu, x=ma, kind="reg")
    ax = plt.gca()
    ax.set_ylabel('Human stomata count')
    ax.set_xlabel('Automatic stomata count')
    return Response(get_plot_as_png(), mimetype="image/png")


@data_export.route('/dataset/<dataset_id_str>/export_err_by_threshold')
def dataset_export_err_by_threshold(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    model = db.get_primary_model()
    plot_err_by_threshold(model=model, dataset_ids=[dataset_id])
    return Response(get_plot_as_png(), mimetype="image/png")


@data_export.route('/export_all')
@requires_admin
def dataset_export_all():
    all_datasets = [export_generator(get_all_samples(dataset['_id']), not i) for i, dataset in enumerate(db.get_datasets())]
    results = chain(*all_datasets)
    dataset_export_name, _ext = os.path.splitext(secure_filename('export_all.csv'))
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition":
                                 "attachment;filename=%s" % dataset_export_name})


@data_export.route('/user_export_all')
def dataset_user_export_all():
    user_id = get_current_user_id()
    datasets = [] if user_id is None else db.get_datasets_by_user(user_id)
    all_datasets = [export_generator(get_all_samples(dataset['_id']), not i) for i, dataset in enumerate(datasets)]
    results = chain(*all_datasets)
    dataset_export_name, _ext = os.path.splitext(secure_filename('user_export_all.csv'))
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition":
                                 "attachment;filename=%s" % dataset_export_name})


@data_export.route('/user_export_human_positions')
def dataset_user_export_human_positions():
    user_id = get_current_user_id()
    datasets = [] if user_id is None else db.get_datasets_by_user(user_id)
    all_datasets = [export_positions_generator(get_all_samples(dataset['_id']), yield_header=not i, human=True)
                    for i, dataset in enumerate(datasets)]
    results = chain(*all_datasets)
    dataset_export_name, _ext = os.path.splitext(secure_filename('user_export_all_human_positions.csv'))
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition": "attachment;filename=%s" % dataset_export_name})


@data_export.route('/user_export_machine_positions')
def dataset_user_export_machine_positions():
    user_id = get_current_user_id()
    datasets = [] if user_id is None else db.get_datasets_by_user(user_id)
    all_datasets = [export_positions_generator(get_all_samples(dataset['_id']), yield_header=not i, human=False)
                    for i, dataset in enumerate(datasets)]
    results = chain(*all_datasets)
    dataset_export_name, _ext = os.path.splitext(secure_filename('user_export_all_machine_positions.csv'))
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition": "attachment;filename=%s" % dataset_export_name})


def export_model_comparison_ds(samples, yield_header, models):
    if yield_header:
        header_fields = ['Name', 'Dataset', 'Manual_count'] + [m['name'] for m in models]
        yield ','.join(header_fields) + '\n'
    model_to_index = {m['_id']: i for i, m in enumerate(models)}
    for sample in samples:
        base_fields = 'name', 'dataset_name', 'human_position_count'
        base_values = [str(sample.get(f, '')) for f in base_fields]
        model_counts = [''] * len(models)
        annotations = db.get_all_model_machine_annotations(sample_id=sample['_id'])
        for annotation in annotations:
            idx = model_to_index.get(annotation['model_id'])
            if idx is not None:
                model_counts[idx] = str(len(annotation['positions']))
        yield ','.join(base_values + model_counts) + '\n'


@data_export.route('/export_model_comparison')
@requires_admin
def export_model_comparison():
    models = db.get_models(status=db.model_status_trained)
    all_datasets = [export_model_comparison_ds(get_all_samples(dataset['_id']), not i, models)
                    for i, dataset in enumerate(db.get_datasets())]
    results = chain(*all_datasets)
    dataset_export_name, _ext = os.path.splitext(secure_filename('export_model_comparison.csv'))
    return Response(results,
                    mimetype="text/plain",
                    headers={"Content-Disposition":
                                 "attachment;filename=%s" % dataset_export_name})


# Test
if __name__ == '__main__':
    for i, dataset in enumerate(db.get_datasets()):
        for r in export_generator(get_all_samples(dataset['_id']), not i):
            print r
