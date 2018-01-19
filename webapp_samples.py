#!/usr/bin/env python
# Individual sample info pages

from flask import Blueprint, redirect, render_template, request
import db
from bson.objectid import ObjectId
from webapp_base import set_error, pop_last_error, error_redirect


samples = Blueprint('samples', __name__, template_folder='templates')


# Names and values to be shown in info table
info_table_entries = (
    ('Image quality - Entropy', 'imq_entropy'),
    ('Image quality - HF mean', 'imq_hf_mean'),
    ('Image quality - HF std', 'imq_hf_std'),
    ('Image quality - HF entropy', 'imq_hf_entropy'),
    ('Image quality - HF threshold frequency', 'imq_hf_threshfreq'),
    ('Image quality - HF power', 'imq_hf_power'),
    ('Image quality - HF skewness', 'imq_hf_skewness'),
    ('Image quality - HF kurtosis', 'imq_hf_kurtosis')
)


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
    info_table = []
    for info_name, info_key in info_table_entries:
        info_value = sample_entry.get(info_key)
        if info_value is not None:
            info_table.append((info_name, info_value))
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
                           next_id=str(next_sample_id), can_annotate_diff=can_annotate_diff, readonly=readonly,
                           info_table=info_table)


# Delete entry
@samples.route('/delete/<str_id>', methods=['POST'])
def delete_entry(str_id):
    # For return path
    id = ObjectId(str_id)
    sample = db.get_sample_by_id(id)
    if sample is None:
        set_error('Item to delete not found.')
        return redirect('/')
    dataset_id = sample['dataset_id']
    readonly = db.is_readonly_dataset_id(dataset_id)
    sample_index, sample_count, prev_sample_id, next_sample_id = db.get_sample_index(dataset_id, id)
    if readonly:
        set_error('Dataset is protected.')
    elif db.delete_sample(id):
        set_error('Item deleted.')
    else:
        set_error('Could not delete item.')
    # Redirect: To next sample in set if it exists. Otherwise to the dataset page.
    if next_sample_id is not None and next_sample_id != id:
        # Return to same kind of page (info/annotation/diff_annotation)
        is_annotation = request.args.get('annotate')
        is_differential = request.args.get('differential')
        if is_annotation:
            suffix = '?differential=1' if is_differential else ''
            return redirect('/annotate/' + str(next_sample_id) + suffix)
        else:
            return redirect('/info/' + str(next_sample_id))
    else:
        return redirect('/dataset/' + str(dataset_id))
