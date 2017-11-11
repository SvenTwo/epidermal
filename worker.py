#!/usr/bin/env python
# Worker process that watches a folder and processes images

import time
import os
from apply_fcn import load_latest_model, process_image_file, plot_heatmap
from config import config
import db
from stoma_counter import compute_stomata_positions
import matplotlib.pyplot as plt
import sys
import subprocess

def set_status(status_string): db.set_status('worker', status_string)
def get_status(): return db.get_status('worker')

def process_images(net, model_id):
    # Process all unprocessed samples
    for sample in db.get_unprocessed_samples():
        image_filename = sample['filename']
        set_status('Processing %s...' % image_filename)
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
            positions = [] # Computed later
            machine_annotation = db.add_machine_annotation(sample['_id'], model_id, heatmap_filename, heatmap_image_filename, positions, net.margin)
            # Count stomata
            heatmap_image = plt.imread(heatmap_image_filename_full)
            positions = compute_stomata_positions(machine_annotation, heatmap_image, plot=False)
            db.update_machine_annotation_positions(sample['_id'], machine_annotation['_id'], positions)
            plt.imsave(heatmap_image_filename_full, heatmap_image)
            print 'Finished record.'
        except Exception, e:
            db.set_sample_error(sample['_id'], "Processing error:\n" +str(e))



EXITCODE_RESTART = 55
restart_signal_filename = os.path.join(config.src_path, 'restart_worker.signal')

def has_restart_signal():
    if os.path.exists(restart_signal_filename):
        os.remove(restart_signal_filename)
        return True
    return False

def send_restart_signal():
    subprocess.call(['touch', restart_signal_filename])

def worker_process():
    # Infinite worker process
    try:
        set_status('Startup...')
        net = load_latest_model()
        model_id = db.get_or_add_model(net.name, net.margin)['_id']
        while True:
            # Restart signal?
            if has_restart_signal():
                return True
            process_images(net, model_id)
            set_status('Waiting for images...')
            time.sleep(1)

    finally:
        set_status('offline')
    return False # Not reached

if __name__ == '__main__':
    # Run self as subprocess to allow restarting
    if len(sys.argv) > 1 and sys.argv[1] == 'proc':
        if worker_process():
            sys.exit(EXITCODE_RESTART)
    else:
        rval = EXITCODE_RESTART
        while rval == EXITCODE_RESTART:
            rval = subprocess.call([sys.argv[0], 'proc'])
        print 'Worker exited with code ', rval
