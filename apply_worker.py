#!/usr/bin/env python
# Worker process that the sample DB and processes unprocessed or queued images

import time
import os
import matplotlib.pyplot as plt
import sys
import subprocess
import traceback

from config import config
from apply_fcn import load_model_by_record, process_image_file, plot_heatmap
import db
from stoma_counter import compute_stomata_positions
from image_measures import get_image_measures


def set_status(status_string, secondary=False):
    status_id = 'sec_worker' if secondary else 'worker'
    db.set_status(status_id, status_string)


def get_status(secondary=False):
    status_id = 'sec_worker' if secondary else 'worker'
    return db.get_status(status_id)


def process_images(net, model):
    # Process all unprocessed samples
    model_id = model['_id']
    is_primary_model = model['primary']
    if is_primary_model:
        unprocessed_samples = db.get_unprocessed_samples()
    else:
        unprocessed_samples = db.get_queued_samples(model_id=model_id)
    for qsample in unprocessed_samples:
        if not is_primary_model:
            db.unqueue_sample(queue_item_id=qsample['_id'])
        sample = db.get_sample_by_id(qsample['sample_id'])
        image_filename = sample['filename']
        set_status('Processing %s...' % image_filename, secondary=not is_primary_model)
        image_filename_full = os.path.join(config.server_image_path, image_filename)
        if not os.path.isfile(image_filename_full):
            db.set_sample_error(sample['_id'], 'File does not exist: "%s".' % image_filename_full)
            continue
        basename, ext = os.path.splitext(image_filename)
        if not ext.lower() in config.image_extensions:
            db.set_sample_error(sample['_id'], 'Unknown file extension "%s".' % ext)
            continue
        try:
            # Lots of saving and loading here. TODO: Should be optimized to be done all in memory.
            # Determine output file paths
            heatmap_filename = os.path.join(net.name, basename + '_heatmap.npy')
            heatmap_filename_full = os.path.join(config.server_heatmap_path, heatmap_filename)
            if not os.path.isdir(os.path.dirname(heatmap_filename_full)):
                os.makedirs(os.path.dirname(heatmap_filename_full))
            heatmap_image_filename = os.path.join(net.name, basename + '_heatmap.jpg')
            heatmap_image_filename_full = os.path.join(config.server_heatmap_path, heatmap_image_filename)
            # Process image
            process_image_file(net, image_filename_full, heatmap_filename_full)
            plot_heatmap(image_filename_full, heatmap_filename_full, heatmap_image_filename_full)
            if 'imq_entropy' not in sample:
                imq = get_image_measures(image_filename_full)
                db.set_image_measures(sample['_id'], imq)
            positions = [] # Computed later
            machine_annotation = db.add_machine_annotation(sample['_id'], model_id, heatmap_filename,
                                                           heatmap_image_filename, positions, net.margin,
                                                           is_primary_model=is_primary_model)
            # Count stomata
            heatmap_image = plt.imread(heatmap_image_filename_full)
            positions = compute_stomata_positions(machine_annotation, heatmap_image, plot=False)
            db.update_machine_annotation_positions(sample['_id'], machine_annotation['_id'], positions,
                                                   is_primary_model=is_primary_model)
            plt.imsave(heatmap_image_filename_full, heatmap_image)
            print 'Finished record.'
        except:
            error_string = traceback.format_exc()
            db.set_sample_error(sample['_id'], "Processing error:\n" +str(error_string))


EXITCODE_RESTART = 55


def worker_process(secondary=False):
    # Infinite worker process
    try:
        set_status('Startup...', secondary=secondary)
        model = None
        # First find network to load
        if secondary:
            set_status('Waiting for model/images...', secondary=secondary)
            while model is None:
                models = db.get_models(details=False, status=db.model_status_trained)
                for cmodel in models:
                    if len(list(db.get_queued_samples(model_id=cmodel['_id']))):
                        model = cmodel
                        break
                if model is None:
                    time.sleep(1)
        else:
            model = db.get_primary_model()
        set_status('Loading model %s...' % model['name'], secondary=secondary)
        net = load_model_by_record(model)
        # Then find samples to process
        while True:
            process_images(net, model)
            # Did the primary model change?
            if not secondary:
                if db.get_primary_model()['_id'] != model['_id']:
                    break
                set_status('Waiting for images...', secondary=secondary)
                time.sleep(1)
            else:
                # Secondary model: Always quit after processing is done; going back to model search.
                break

    finally:
        set_status('offline', secondary=secondary)

    # Trigger restart.
    return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Epidermal worker process: Finds stomata in images.')
    parser.add_argument('--run', action='store_true', help='Run the actual process. Otherwise, start process as child.')
    parser.add_argument('--secondary', action='store_true', help='Monitor non-primary models.')

    args = parser.parse_args()
    if args.run:
        if worker_process(args.secondary):
            sys.exit(EXITCODE_RESTART)
    else:
        cmdline = list(sys.argv) + ['--run']
        rval = EXITCODE_RESTART
        while rval == EXITCODE_RESTART:
            rval = subprocess.call(cmdline)
            time.sleep(1)
        print 'Worker exited with code ', rval
