#!/usr/bin/env python2
# Retrain the Stomata identifier CNN

import os
import sys
import time
from config import config
import subprocess
from archive2dataset import db2patches, patches2filelist
from convert_model_to_fcn import convert_epi1
import db
from bson.objectid import ObjectId


def set_status(status_string):
    db.set_status('trainer', status_string)


def get_status():
    return db.get_status('trainer')


def imagelist2lmdb(image_root, imagelist_filename, lmdb_filename):
    print 'imagelist2lmdb to %s' % lmdb_filename
    if os.path.exists(lmdb_filename):
        print 'Exists. Skipping.'
        return
    cnv_cmd = os.path.join(config.caffe_path, 'tools', 'convert_imageset')
    cmd = [cnv_cmd, image_root + '/', imagelist_filename, lmdb_filename]
    if subprocess.call(cmd):
        raise RuntimeError('Error generating LMDB.')
    print 'LMDB created at %s' % lmdb_filename


def train(model_id):
    # Fetch model info
    model = db.get_model_by_id(model_id)
    train_label = model['train_tag']
    # Prepare data
    # TODO: Data limit; dataset size back into DB
    exec_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cnn'))
    exec_path = os.path.join(exec_base_path, str(model_id))
    os.makedirs(exec_path, exist_ok=True)
    output_path = os.path.join(config.train_data_path, str(model_id), 'samples')
    os.makedirs(output_path, exist_ok=True)
    db2patches(output_path, train_label=train_label)
    patches2filelist(output_path)
    for dset in ('train', 'val', 'test'):
        imagelist_filename = os.path.join(output_path, dset + '.txt')
        lmdb_filename =  os.path.join(output_path, dset + '_lmdb')
        imagelist2lmdb(output_path, imagelist_filename, lmdb_filename)
        exec_lmdb_filename = os.path.join(exec_path, dset + '_lmdb')
        if os.path.islink(exec_lmdb_filename):
            os.remove(exec_lmdb_filename)
        os.symlink(lmdb_filename, exec_lmdb_filename)
    # Prepare folder for processing
    os.chdir(exec_path)
    for fnbase in 'alexnet', 'alexnetfcn', 'solver_alexnetftc', 'solver_alexnetscratch':
        fn = fnbase + '.prototxt'
        os.symlink(os.path.join(exec_base_path, fn), os.path.join(exec_path, fn))
    cnn_output_path = os.path.join(exec_path, 'out')
    if os.path.islink(cnn_output_path):
        os.remove(cnn_output_path)
    real_cnn_output_path = os.path.join(output_path, 'cnn')
    if not os.path.isdir(real_cnn_output_path):
        os.makedirs(real_cnn_output_path)
    print 'Link %s to %s' % (real_cnn_output_path, cnn_output_path)
    os.symlink(real_cnn_output_path, cnn_output_path)
    # Run caffe!
    caffe_cmd = os.path.join(config.caffe_path, 'tools', 'caffe')
    cmd = [caffe_cmd, 'train', '--solver', 'solver_alexnetftc.prototxt', '--weights', config.caffe_train_baseweights] + config.caffe_train_options.split(' ')
    print cmd
    if subprocess.call(cmd):
        raise RuntimeError('Error calling caffe.')
    # Convert to fully convolutional network
    convert_epi1()


def run_daemon():
    set_status('Daemon startup...')
    while True:
        scheduled_models = list(db.get_models(db.model_status_scheduled))
        if len(scheduled_models):
            model = scheduled_models[0]
            set_status('Train model %s (%s)...' % (model['_name'], str(model['_id'])))
            cmdline = list(sys.argv) + ['--model-id', str(model['_id'])]
            subprocess.call(cmdline)
        set_status('Waiting for scheduled models...')
        time.sleep(1)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Epidermal worker process: Train network from annotated images.')
    parser.add_argument('--model-id', type=str, help='Database entry of model to train. If not specified, start as a '
                                                     'daemon that watches the DB and creates child processes to train '
                                                     'as needed.')

    args = parser.parse_args()
    if args.model_id is None:
        run_daemon()
    else:
        try:
            train(ObjectId(args.model_id))
        except:
            db.set_model_status(ObjectId(args.model_id), db.model_status_failed)

