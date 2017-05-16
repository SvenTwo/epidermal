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
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
import numpy as np

data_export = Blueprint('data_export', __name__, template_folder='templates')

def export_generator(samples):
    yield 'Name,Status,Manual_count,Automatic_count\n'
    for s in samples:
        if s['error']:
            status = 'ERROR'
        elif not s['processed']:
            status = 'QUEUED'
        else:
            status = 'OK'
        yield ','.join([s['name'], status, str(s.get('human_position_count')), str(s.get('machine_position_count'))]) + '\n'

@data_export.route('/dataset/<dataset_id_str>/export')
def dataset_export(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    enqueued = db.get_unprocessed_samples(dataset_id=dataset_id)
    finished = db.get_processed_samples(dataset_id=dataset_id)
    errored = db.get_error_samples(dataset_id=dataset_id)
    results = export_generator(enqueued + finished + errored)
    dataset_export_name, _ext = os.path.splitext(secure_filename(dataset_info['name']))
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
    sns.regplot(y=hu, x=ma)
    ax = plt.gca()
    ax.set_ylabel('Human stomata count')
    ax.set_xlabel('Automatic stomata count')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return Response(buf, mimetype="image/png")
