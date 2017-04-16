#!/usr/bin/env python
# Stomata identification server: Basically just lists the erever contents

import os
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import paths
import db
from PIL import Image
from bson.objectid import ObjectId

app = Flask(__name__)
app.debug = True

# Error handling
app.epi_last_error = None
def set_error(msg): app.epi_last_error = msg
def error_redirect(msg):
    set_error(msg)
    return redirect(request.url)
def pop_last_error():
    last_error = app.epi_last_error
    app.epi_last_error = None
    return last_error

# Upload
def allowed_file(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in paths.image_extensions

def upload_file(dataset_id):
    # check if the post request has the file part
    if 'file' not in request.files: return error_redirect('No file.')
    file = request.files['file']
    if file.filename == '': return error_redirect('Empty file.')
    if (not file) or (not allowed_file(file.filename)): return error_redirect('Invalid or disallowed file type.')
    basename, ext = os.path.splitext(secure_filename(file.filename))
    # Make unique filename
    filename = basename + ext
    i = 1
    while True:
        full_fn = os.path.join(paths.server_image_path, filename)
        if not os.path.isfile(full_fn): break
        filename = '%s-%03d%s' % (basename, i, ext)
        i += 1
    # Save it
    file.save(full_fn)
    # Add DB entry (after file save to worker can pick it up immediately)
    entry = db.add_sample(filename, dataset_id=dataset_id)
    # Image size
    try:
        image = Image.open(full_fn)
        db.set_sample_data(entry['_id'], image.size)
    except:
        db.set_sample_error(entry['_id'], 'Error loading image.')
        set_error('Could not load image. Invalid / Upload error?')
    # Redirect to file info
    return redirect('/info/%s' % str(entry['_id']))


# Entry info page
@app.route('/info/<id>')
def show_info(id):
    # Query info from DB
    sample_id = ObjectId(id)
    sample_entry = db.get_sample_by_id(sample_id)
    # Unknown entry?
    if sample_entry is None:
        return error_redirect('Unknown entry: "%s".' % str(sample_id))
    # Determine data
    refresh = False
    filename = sample_entry['filename']
    annotations = []
    if sample_entry['error']:
        info_string = 'Error: ' + sample_entry['error_string']
    elif not sample_entry['processed']:
        info_string = 'Processing...'
        annotations += [{'image_filename': 'images/' + filename, 'title': 'Input image', 'info_string': ''}]
        refresh = True
    else:
        info_string = 'Processed.'
        annotation_data = db.get_machine_annotations(sample_id)
        for ad in annotation_data:
            model_data = db.get_model_by_id(ad['model_id'])
            an = {}
            if model_data is None:
                an['info_string'] = '??? Unknown model ???'
                an['title'] = 'Unknown'
            else:
                an['title'] = model_data['name']
                an['info_string'] = 'Margin: %d' % model_data['margin']
            an['image_filename'] = 'heatmaps/' + ad['heatmap_image_filename']
            annotations += [an]
    return render_template("info.html", id=id, filename=filename, info_string=info_string, annotations=annotations, error=pop_last_error(), refresh=refresh)


# Delete entry
@app.route('/delete/<dataset_id>/<id>', methods=['POST'])
def delete_entry(dataset_id, id):
    # Delete by ID
    if db.delete_sample(ObjectId(id)):
        set_error('Item deleted.')
    else:
        set_error('Item to delete not found.')
    return redirect('/dataset/' + dataset_id)

@app.route('/about')
def about(): return render_template("about.html", error=pop_last_error())


# Add dataset
@app.route('/add_dataset', methods=['POST'])
def add_dataset():
    print 'Adding dataset.', request.form
    # Add by name. Forward to newly created dataset
    dataset_name = request.form['dataset_name'].strip()
    if dataset_name == '':
        set_error('Invalid dataset name.')
        return redirect('/')
    print 'Name: %s' % dataset_name
    dataset_info = db.get_dataset_by_name(dataset_name)
    print 'Info: %s' % str(dataset_info)
    if dataset_info is not None:
        set_error('Duplicate dataset name.')
        return redirect('/')
    dataset_info = db.add_dataset(dataset_name)
    print 'Info: %s' % str(dataset_info)
    return redirect('/dataset/' + str(dataset_info['_id']))


# Delete dataset
@app.route('/delete_dataset/<dataset_id_str>', methods=['POST'])
def delete_dataset(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    if dataset_info is None:
        return render_template("404.html")
    db.delete_dataset(dataset_id)
    set_error('Dataset "%s" deleted.' % dataset_info['name'])
    return redirect('/')

# Main overview page within a dataset
@app.route('/dataset/<dataset_id_str>', methods=['GET', 'POST'])
def dataset_info(dataset_id_str):
    dataset_id = ObjectId(dataset_id_str)
    dataset_info = db.get_dataset_by_id(dataset_id)
    if dataset_info is None:
        return render_template("404.html")
    if request.method == 'POST':
        # File upload
        return upload_file(dataset_id)
    enqueued = db.get_unprocessed_samples()
    finished = db.get_processed_samples(dataset_id=dataset_id)
    errored = db.get_error_samples(dataset_id=dataset_id)
    # Get request data
    return render_template("dataset.html", dataset_name=dataset_info['name'], dataset_id=dataset_id_str, enqueued=enqueued, finished=finished, errored=errored, status=db.get_status('worker'), error=pop_last_error())


# List of datasets page
@app.route('/')
def overview():
    datasets = db.get_datasets()
    enqueued = db.get_unprocessed_samples()
    return render_template("index.html", datasets=datasets, enqueued=enqueued, status=db.get_status('worker'), error=pop_last_error())


# Start flask app
app.run(host='0.0.0.0', port=7900)
