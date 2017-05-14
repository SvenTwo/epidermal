#!/usr/bin/env python
# Stomata identification server: Basically just lists the erever contents

import os
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import db
from PIL import Image
from bson.objectid import ObjectId
import json
from config import config
from zipfile import ZipFile
from webapp_admin import admin
from webapp_export import data_export

app = Flask(__name__)
app.debug = True
app.register_blueprint(admin)
app.register_blueprint(data_export)

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
def upload_file(dataset_id):
    # check if the post request has the file part
    if 'file' not in request.files: return error_redirect('No file.')
    file = request.files['file']
    if file.filename == '': return error_redirect('Empty file.')
    if (not file): return error_redirect('Invalid file.')
    # Generate server-side filename
    basename, ext = os.path.splitext(secure_filename(file.filename))
    filename = basename + ext
    # Generate dataset if needed
    if dataset_id is None:
        dataset_id = db.add_dataset(name=filename)['_id']
    # Handle according to type
    if ext in config.archive_extensions:
        return upload_archive(dataset_id, file, filename)
    elif ext in config.image_extensions:
        return upload_image(dataset_id, file, filename)
    else:
        return error_redirect('Invalid or disallowed file type.')

def make_unique_server_image_filename(filename):
    basename, ext = os.path.splitext(filename)
    filename = basename + ext
    i = 1
    while True:
        full_fn = os.path.join(config.server_image_path, filename)
        if not os.path.isfile(full_fn): break
        filename = '%s-%03d%s' % (basename, i, ext)
        i += 1
    return full_fn

def upload_archive(dataset_id, file, filename):
    zipf = ZipFile(file.stream, 'r')
    print 'ZIPF:'
    for nfo in zipf.infolist():
        if nfo.file_size > config.max_image_file_size:
            return error_redirect('One of the images (%s) exceeds the max file size (%d).' % (nfo.filename, config.max_image_file_size))
    n_added = 0
    for nfo in zipf.infolist():
        # Check
        image_filename = secure_filename(nfo.filename)
        basename, ext = os.path.splitext(image_filename)
        if ext not in config.image_extensions:
            print 'Not an image: %s (%s)' % (ext, image_filename)
            continue
        # Extract
        full_fn = make_unique_server_image_filename(image_filename)
        file = zipf.open(nfo)
        with open(full_fn, 'wb') as fid:
            contents = file.read()
            fid.write(contents)
        print 'Written to ', full_fn
        # Add
        if add_uploaded_image(dataset_id, full_fn, image_filename) is not None:
            n_added += 1
        else:
            # Cleanup invalid
            if os.path.isfile(full_fn):
                os.remove(full_fn)
    set_error('%d images added.' % n_added)
    return redirect('/dataset/%s' % str(dataset_id))


def upload_image(dataset_id, file, filename):
    # Make unique filename
    full_fn = make_unique_server_image_filename(filename)
    # Save it
    file.save(full_fn)
    # Process
    entry = add_uploaded_image(dataset_id, full_fn, filename)
    # Redirect to file info
    #return redirect('/info/%s' % str(entry['_id']))
    return redirect('/dataset/%s' % str(dataset_id))

def add_uploaded_image(dataset_id, full_fn, filename):
    # Get some image info
    try:
        im = Image.open(full_fn)
    except:
        print 'Invalid image file: %s' % full_fn
        set_error('Could not load image. Invalid / Upload error?')
        return None
    # Add DB entry (after file save to worker can pick it up immediately)
    entry = db.add_sample(name=filename, filename=os.path.basename(full_fn), size=im.size, dataset_id=dataset_id)
    # Return added entry
    return entry


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
    name = sample_entry['name']
    dataset_id = str(sample_entry['dataset_id'])
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
        an = {}
        an['info_string'] = ''
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
            an['title'] = 'By user %s' % ad['user_name']
        positions = ad['positions']
        if positions is not None:
            an['info_string'] += ' %d stomata' % len(positions)
        annotations += [an]
    if not has_image_output:
        annotations += [{'image_filename': 'images/' + filename, 'title': 'Input image', 'info_string': ''}]
    return render_template("info.html", id=id, name=name, dataset_id=dataset_id, info_string=info_string, annotations=annotations, error=pop_last_error(), refresh=refresh)


# Annotation page
@app.route('/annotate/<id>', methods=['GET', 'POST'])
def annotate(id):
    # Query info from DB
    sample_id = ObjectId(id)
    sample_entry = db.get_sample_by_id(sample_id)
    # Unknown entry?
    if sample_entry is None:
        return error_redirect('Unknown entry: "%s".' % str(sample_id))
    # Determine data
    image_filename = 'images/' + sample_entry['filename']
    info_string = ''
    annotations = db.get_human_annotations(sample_id)
    if len(annotations):
        annotations_json = annotations[0]['positions']
    else:
        annotations_json = []
    return render_template("annotate.html", id=id, image_filename=image_filename, info_string=info_string, error=pop_last_error(),
                           height=sample_entry['size'][1], width=sample_entry['size'][0], annotations=annotations_json, margin=96)


# Save annotations
@app.route('/save_annotations/<id>', methods=['GET', 'POST'])
def save_annotations(id):
    # Add by name. Forward to newly created dataset
    annotations = json.loads(request.form['annotations'].strip())
    margin = int(request.form['margin'].strip())
    print 'Saving annotations.', id, margin, annotations
    db.set_human_annotation(ObjectId(id), db.get_default_user(), annotations, margin)
    return redirect('/info/' + id)


# Delete entry
@app.route('/delete/<id>', methods=['POST'])
def delete_entry(id):
    # For return path
    sample = db.get_sample_by_id(ObjectId(id))
    if sample is None:
        set_error('Item to delete not found.')
        return redirect('/')
    dataset_id = sample['dataset_id']
    # Delete by ID
    if db.delete_sample(ObjectId(id)):
        set_error('Item deleted.')
    else:
        set_error('Could not delete item.')
    return redirect('/dataset/' + str(dataset_id))

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
    if dataset_id_str == 'new' and request.method == 'POST':
        dataset_id = None
    else:
        dataset_id = ObjectId(dataset_id_str)
        dataset_info = db.get_dataset_by_id(dataset_id)
        if dataset_info is None:
            return render_template("404.html")
    if request.method == 'POST':
        # File upload
        return upload_file(dataset_id)
    enqueued = db.get_unprocessed_samples(dataset_id=dataset_id)
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
app.run(host='0.0.0.0', port=9000)
