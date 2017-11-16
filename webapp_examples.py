#!/usr/bin/env python
# Example dataset

from flask import Blueprint, redirect
from webapp_base import set_error
import db

examples = Blueprint('examples', __name__, template_folder='templates')

@examples.route('/examples')
def examples_page():
    # Find the example dataset
    example_dataset = db.get_example_dataset()
    if example_dataset is None:
        set_error('No example dataset defined.')
        return redirect('/')
    return redirect('/dataset/%s' % example_dataset['_id'])
