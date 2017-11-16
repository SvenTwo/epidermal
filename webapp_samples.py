#!/usr/bin/env python
# Individual sample info pages

from flask import Blueprint, redirect, render_template
import db
from bson.objectid import ObjectId
from webapp_base import set_error, pop_last_error, error_redirect


samples = Blueprint('samples', __name__, template_folder='templates')


# Entry info page
@samples.route('/info/<sid>')
def show_info(sid):
    # Query info from DB
    sample_id = ObjectId(sid)
    sample_entry = db.get_sample_by_id(sample_id)
    sample_index, sample_count, prev_sample_id, next_sample_id = db.get_sample_index(sample_entry['dataset_id'],
                                                                                     sample_id)
    # Unknown entry?
    if sample_entry is None:
        return error_redirect('Unknown entry: "%s".' % str(sample_id))
    # Allow fixing of machine annotation? Only if not human-annotated and there is a machine annotation with stomata
    can_annotate_diff = (not sample_entry['annotated']) and (sample_entry['machine_position_count'])
    # Determine data
    refresh = False
    filename = sample_entry['filename']
    name = sample_entry['name']
    dataset_id = sample_entry['dataset_id']
    readonly = db.is_readonly_dataset_id(dataset_id)
    annotations = []
    if sample_entry['error']:
        info_string = 'Error: ' + sample_entry['error_string']
    elif not sample_entry['processed']:
        info_string = 'Processing...'
        refresh = True
    else:
        info_string = 'Processed.'
    annotation_data = db.get_machine_annotations(sample_id) + db.get_human_annotations(sample_id)
    has_image_output = False
    for ad in annotation_data:
        model_id = ad.get('model_id')
        an = {'info_string': ''}
        if model_id is not None:
            model_data = db.get_model_by_id(model_id)
            if model_data is None:
                an['info_string'] += '??? Unknown model ???'
                an['title'] = 'Unknown'
            else:
                an['title'] = model_data['name']
                an['info_string'] += 'Margin: %d' % model_data['margin']
            an['image_filename'] = 'heatmaps/' + ad['heatmap_image_filename']
            has_image_output = True
        else:
            an['title'] = 'By user %s' % ad.get('user_name')
        positions = ad['positions']
        if positions is not None:
            an['info_string'] += ' %d stomata' % len(positions)
        annotations += [an]
    annotations = reversed(annotations)
    if not has_image_output:
        annotations += [{'image_filename': 'images/' + filename, 'title': 'Input image', 'info_string': ''}]
    return render_template("info.html", id=sid, name=name, dataset_id=str(dataset_id), info_string=info_string,
                           annotations=annotations, error=pop_last_error(), refresh=refresh,
                           sample_index=sample_index, sample_count=sample_count, prev_id=str(prev_sample_id),
                           next_id=str(next_sample_id), can_annotate_diff=can_annotate_diff, readonly=readonly)


# Delete entry
@samples.route('/delete/<id>', methods=['POST'])
def delete_entry(id):
    # For return path
    sample = db.get_sample_by_id(ObjectId(id))
    if sample is None:
        set_error('Item to delete not found.')
        return redirect('/')
    dataset_id = sample['dataset_id']
    readonly = db.is_readonly_dataset_id(dataset_id)
    if readonly:
        set_error('Dataset is protected.')
    elif db.delete_sample(ObjectId(id)):
        set_error('Item deleted.')
    else:
        set_error('Could not delete item.')
    return redirect('/dataset/' + str(dataset_id))
