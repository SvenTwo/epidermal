#!/usr/bin/env python2.7
# CLI tool to add a model with existing weights to the DB.

import os
import sys
import shutil

import db
from config import config


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='CLI tool to add a model with existing weights to the DB.')
    parser.add_argument('--name',
                        type=str,
                        required=True,
                        help='Name to be used in admin interface.')
    parser.add_argument('--weights-filename',
                        type=str,
                        required=True,
                        help='caffe weights file for processing CNN.')
    parser.add_argument('--proto-filename',
                        type=str,
                        required=True,
                        help='caffe CNN definition prototxt file.')
    parser.add_argument('--primary',
                        action='store_true',
                        help='If passed, mark this as the new primary model to be used by the apply_worker.')
    parser.add_argument('--move-files',
                        action='store_true',
                        help='If passed, move files to CNN folder instead of copying.')
    parser.add_argument('--margin',
                        type=int,
                        default=96,
                        help='Margin left at borders by convolutions.')

    args = parser.parse_args()

    # Safety
    if not os.path.isfile(args.weights_filename):
        print 'Weights file not found: ', args.weights_filename
        sys.exit(1)
    if not os.path.isfile(args.proto_filename):
        print 'Network definition file not found: ', args.weights_filename
        sys.exit(1)

    # Add model
    print 'Adding model...'
    rec = db.add_model(model_name=args.name,
                       margin=args.margin,
                       status=db.model_status_trained)
    print 'Model added as', rec['_id']

    # Copy/Move model files. Using hardcoded names for default parameters defined by apply_fn.py
    cnn_dir = os.path.join(config.get_cnn_path(), str(rec['_id']))
    cnn_weights_dir = os.path.join(cnn_dir, 'out')
    os.makedirs(cnn_weights_dir)

    def init_file(src, dst):
        if args.move_files:
            print 'mv %s -> %s' % (src, dst)
            shutil.move(src, dst)
        else:
            print 'cp %s -> %s' % (src, dst)
            shutil.copy(src, dst)

    init_file(args.proto_filename, os.path.join(cnn_dir, 'alexnetfcn.prototxt'))
    init_file(args.weights_filename, os.path.join(cnn_weights_dir, 'alexnetftc_iter_5000_fcn.caffemodel'))

    # Set as primary
    if args.primary:
        print 'Update primary model...'
        db.set_primary_model(rec['_id'])
        print 'Primary updated.'
