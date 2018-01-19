#!/usr/bin/env python
# User dataset functions

from flask import render_template, Blueprint, redirect, request
from bson.objectid import ObjectId
from webapp_base import pop_last_error, set_error
from webapp_users import get_current_user_id
from flask_security import current_user
import db
from urllib import unquote_plus
import json

user_datasets = Blueprint('user_datasets', __name__, template_folder='templates')


@user_datasets.route('/user_datasets')
def user_datasets_page():
    # Claim any unowned datasets
    try:
        added_datasets = json.loads(unquote_plus(request.cookies['datasets']))
        for added_dataset in added_datasets:
            do_claim_dataset(added_dataset, ignore_errors=True)
    except:
        pass
    # Render page, which will reset the unowned datasets variable
    user_id = get_current_user_id()
    datasets = [] if user_id is None else db.get_datasets_by_user(user_id)
    return render_template('user_datasets.html', datasets=datasets, error=pop_last_error())


@user_datasets.route('/claim_dataset/<dataset_id_str>')
def claim_dataset(dataset_id_str):
    do_claim_dataset(dataset_id_str, ignore_errors=False)

def do_claim_dataset(dataset_id_str, ignore_errors):
    dataset_id = ObjectId(dataset_id_str)
    if current_user is None:
        if ignore_errors:
            return
        set_error('Not logged in.')
        return redirect('/dataset/' + dataset_id_str)
    dataset = db.get_dataset_by_id(dataset_id)
    if dataset is None:
        if ignore_errors:
            return
        set_error('Dataset not found.')
        return redirect('/user_datasets')
    if dataset.get('user') is not None:
        if ignore_errors:
            return
        set_error('Dataset already owned by %s.' % dataset['user'].get('email'))
        return redirect('/dataset/' + dataset_id_str)
    db.set_dataset_user(dataset_id, current_user.id)
    return redirect('/user_datasets')
