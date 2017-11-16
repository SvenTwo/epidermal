#!/usr/bin/env python
# Annotate samples functions

from flask import Blueprint, redirect, request, render_template
import db
import json
from bson.objectid import ObjectId
from webapp_base import set_error, pop_last_error, error_redirect

annotations = Blueprint('annotations', __name__, template_folder='templates')

# Annotation page
@annotations.route('/annotate/<sid>', methods=['GET', 'POST'])
def annotate(sid):
    # Query info from DB
    sample_id = ObjectId(sid)
    sample_entry = db.get_sample_by_id(sample_id)
    dataset_id = sample_entry['dataset_id']
    readonly = db.is_readonly_dataset_id(dataset_id)
    sample_index, sample_count, prev_sample_id, next_sample_id = db.get_sample_index(dataset_id, sample_id)
    # Unknown entry?
    if sample_entry is None:
        return error_redirect('Unknown entry: "%s".' % str(sample_id))
    # Determine data
    image_filename = 'images/' + sample_entry['filename']
    info_string = ''
    # Differential? Then load machine annotations, unless there are human annotations already
    annotations = db.get_human_annotations(sample_id)
    is_differential = request.args.get('differential')
    if is_differential and not annotations:
        annotations = db.get_machine_annotations(sample_id)
    if len(annotations):
        annotations_json = annotations[0]['positions']
        # Machine annotations are in a different format
        if len(annotations_json) and isinstance(annotations_json[0], list):
            annotations_json = [{'x': a[0], 'y': a[1]} for a in annotations_json]
    else:
        annotations_json = []
    return render_template("annotate.html", id=sid, image_filename=image_filename, info_string=info_string,
                           error=pop_last_error(), height=sample_entry['size'][1], width=sample_entry['size'][0],
                           annotations=annotations_json, margin=96, dataset_id=str(dataset_id),
                           sample_index=sample_index, sample_count=sample_count, prev_id=str(prev_sample_id),
                           next_id=str(next_sample_id), is_differential=is_differential, readonly=readonly)


# Save annotations
@annotations.route('/save_annotations/<sid>', methods=['GET', 'POST'])
def save_annotations(sid):
    sample_id = ObjectId(sid)
    sample_entry = db.get_sample_by_id(sample_id)
    # Caution: Load dataset id from DB (not from form), for security of the readonly check!
    # dataset_id = ObjectId(request.form['dataset_id'].strip())
    dataset_id = sample_entry['dataset_id']
    readonly = db.is_readonly_dataset_id(dataset_id)
    if readonly:
        set_error('Dataset is protected.')
        return redirect('/dataset/' + str(dataset_id))
    is_differential = request.args.get('differential')
    if is_differential:
        base_annotations = db.get_machine_annotations(sample_id)
        redirect_params = '?differential=1'
    else:
        base_annotations = None
        redirect_params = ''
    # Save annotations for sample
    annotations = json.loads(request.form['annotations'].strip())
    margin = int(request.form['margin'].strip())
    print 'Saving annotations.', sid, margin, annotations
    db.set_human_annotation(sample_id, db.get_default_user(), annotations, margin, base_annotations=base_annotations)
    # Forward either to info page or to annotation of next un-annotated entry in DB if found
    annotate_next = ("save_and_continue" in request.form)
    if annotate_next:
        next_sample_id = db.get_next_sample_id(dataset_id, sample_id, annotated=False)
        if next_sample_id is not None:
            return redirect('/annotate/' + str(next_sample_id) + redirect_params)
        else:
            set_error('No more samples to annotate.')
            return redirect('/dataset/' + str(dataset_id))
    # Nothing
    return redirect('/info/' + sid)

