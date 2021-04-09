#!/usr/bin/env python
# Worker process that the sample DB and processes unprocessed or queued images

import time
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import subprocess
import traceback
from tqdm import tqdm
import random

from config import config, add_config_option
from apply_fcn_caffe import process_image_file, plot_heatmap, prob_to_fc8
from apply_fcn import load_model_by_record
import db
from stoma_counter import compute_stomata_positions, default_prob_threshold
from image_measures import get_image_measures


def set_status(status_string, secondary=False):
    status_id = 'sec_worker' if secondary else 'worker'
    db.set_status(status_id, status_string)


def get_status(secondary=False):
    status_id = 'sec_worker' if secondary else 'worker'
    return db.get_status(status_id)


def process_primary_model(net, model):
    # Process all unprocessed samples
    model_id = model['_id']
    unprocessed_samples = db.get_unprocessed_samples()
    for qsample in unprocessed_samples:
        process_image_sample(net=net,
                             model_id=model_id,
                             sample_id=qsample['_id'],
                             is_primary_model=True)


def process_secondary_models(net, model):
    # Process all unprocessed samples
    model_id = model['_id']
    while True:
        unprocessed_samples = list(db.get_queued_samples(model_id=model_id))
        if not len(unprocessed_samples):
            break
        qsample = unprocessed_samples[0]
        db.unqueue_sample(queue_item_id=qsample['_id'])
        if 'sample_id' in qsample:
            process_image_sample(net=net,
                                 model_id=model_id,
                                 sample_id=qsample['sample_id'],
                                 is_primary_model=False)
        elif 'validation_model_id' in qsample:
            process_validation_set(net, model, db.get_model_by_id(qsample['validation_model_id']))
        else:
            print 'Invalid sample:', qsample


# Process all training and validation images of a model training run
def process_validation_set(net, net_model, validation_set_model, sample_limit=10000):
    # List images
    sample_path = os.path.join(config.get_train_data_path(), str(validation_set_model['_id']), 'samples')
    for subset in 'test', 'train':
        set_status('Processing model %s %s set %s...' % (net_model['name'], subset, validation_set_model['name']))
        imagelist_filename = os.path.join(sample_path, subset + '.txt')
        image_list = [s.split(' ') for s in open(imagelist_filename, 'rt').read().splitlines()]
        n_images = len(image_list)
        if n_images > sample_limit:
            image_list = random.sample(image_list, sample_limit)
            n_images = sample_limit
        confusion_matrix = [[0, 0], [0, 0]]
        predictions = [{}, {}]
        for i, (image_path, true_label_string) in tqdm(enumerate(image_list), total=len(image_list)):
            set_status('Processing model %s %s set %s... (%d/%d)' % (net_model['name'], subset,
                                                                     validation_set_model['name'],
                                                                     i, n_images))
            image_filename_full = os.path.join(sample_path, image_path)
            data = process_image_file(net, image_filename_full, crop=True, verbose=False)
            probs = data['probs']
            prediction = int(probs.item() > 0)
            true_label = int(true_label_string)
            confusion_matrix[true_label][prediction] += 1
            predictions[true_label][image_path] = probs.item()
        print '%s %s %s confusion_matrix: %s' % (net_model['name'], subset, validation_set_model['name'],
                                                 confusion_matrix)
        # Get worst predictions for both classes
        worst_predictions = {k: sorted(p.iteritems(), key=lambda i: i[1] * s)[:25]
                             for p, s, k in zip(predictions, (-1, +1), ('Distractor', 'Target'))}
        # Store all in DB
        db.save_validation_results(train_model_id=net_model['_id'],
                                   validation_model_id=validation_set_model['_id'],
                                   image_subset=subset,
                                   confusion_matrix=confusion_matrix,
                                   worst_predictions=worst_predictions)


default_image_zoom_values = {
    'default': None,
    'small': [2.0],
    'tiny': [4.0],
}



def process_image_sample(net, model_id, sample_id, is_primary_model):
    sample = db.get_sample_by_id(sample_id)
    if sample is None:
        return
    dataset_info = db.get_dataset_by_id(sample['dataset_id'])
    image_zoom_values = default_image_zoom_values.get(dataset_info.get('image_zoom'))
    threshold_prob_val = dataset_info.get('threshold_prob')
    if not threshold_prob_val:
        threshold_prob = default_prob_threshold
    else:
        threshold_prob = prob_to_fc8(threshold_prob_val)
    image_filename = sample['filename']
    set_status('Processing %s...' % image_filename, secondary=not is_primary_model)
    image_filename_full = os.path.join(config.get_server_image_path(), image_filename)
    if not os.path.isfile(image_filename_full):
        db.set_sample_error(sample['_id'], 'File does not exist: "%s".' % image_filename_full)
        return
    basename, ext = os.path.splitext(image_filename)
    if not ext.lower() in config.image_extensions:
        db.set_sample_error(sample['_id'], 'Unknown file extension "%s".' % ext)
        return
    try:
        # Lots of saving and loading here. TODO: Should be optimized to be done all in memory.
        # Determine output file paths
        heatmap_filename = os.path.join(net.name, basename + '_heatmap.npz')
        heatmap_filename_full = os.path.join(config.get_server_heatmap_path(), heatmap_filename)
        if not os.path.isdir(os.path.dirname(heatmap_filename_full)):
            os.makedirs(os.path.dirname(heatmap_filename_full))
        heatmap_image_filename = os.path.join(net.name, basename + '_heatmap.jpg')
        heatmap_image_filename_full = os.path.join(config.get_server_heatmap_path(), heatmap_image_filename)
        # Process image
        data = process_image_file(net, image_filename_full, heatmap_filename_full, scales=image_zoom_values)
        plot_heatmap(image_filename_full, heatmap_filename_full, heatmap_image_filename_full)
        if 'imq_entropy' not in sample:
            imq = get_image_measures(image_filename_full)
            db.set_image_measures(sample['_id'], imq)
        positions = [] # Computed later
        machine_annotation = db.add_machine_annotation(sample['_id'], model_id, heatmap_filename,
                                                       heatmap_image_filename, positions,
                                                       margin=int(net.margin / data['scale']),
                                                       is_primary_model=is_primary_model,
                                                       scale=data['scale'])
        # Count stomata
        heatmap_image = plt.imread(heatmap_image_filename_full)
        positions = compute_stomata_positions(machine_annotation, heatmap_image, plot=False,
                                              prob_threshold=threshold_prob)
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
            if secondary:
                process_secondary_models(net, model)
                # Secondary model: Always quit after processing is done; going back to model search.
                break
            else:
                process_primary_model(net, model)
                # Did the primary model change?
                if db.get_primary_model()['_id'] != model['_id']:
                    break
                set_status('Waiting for images...', secondary=secondary)
                time.sleep(1)
    finally:
        set_status('offline', secondary=secondary)

    # Trigger restart.
    return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Epidermal worker process: Finds stomata in images.')
    parser.add_argument('--run', action='store_true', help='Run the actual process. Otherwise, start process as child.')
    parser.add_argument('--secondary', action='store_true', help='Monitor non-primary models.')
    add_config_option(parser)

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
