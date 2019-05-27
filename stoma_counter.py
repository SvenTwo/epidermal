#!/usr/bin/env python
# Count stomata from heatmap

import os
import numpy as np
from scipy.ndimage import imread

import db
from config import config
from stoma_counter_peaks import compute_stomata_positions_on_prob, default_prob_threshold, default_prob_area_threshold


def compute_stomata_positions(machine_annotation, heatmap_image, plot=False, do_contour=False, do_peaks=True,
                              prob_threshold=default_prob_threshold,
                              prob_area_threshold=default_prob_area_threshold):
    # Load heatmap + image
    heatmap_filename = os.path.join(config.get_server_heatmap_path(), machine_annotation['heatmap_filename'])
    print 'Counting thresh %f on heatmap %s' % (prob_threshold, heatmap_filename)
    sample_info = db.get_sample_by_id(machine_annotation['sample_id'])
    # Derive zoom
    data = np.load(heatmap_filename)
    return compute_stomata_positions_on_prob(probs=data['probs'],
                                             scale=data['scale'],
                                             margin=machine_annotation['margin'],
                                             sample_size=sample_info['size'],
                                             heatmap_image=heatmap_image,
                                             plot=plot,
                                             do_contour=do_contour,
                                             do_peaks=do_peaks,
                                             prob_threshold=prob_threshold,
                                             prob_area_threshold=prob_area_threshold)


def compute_stomata_positions_for_sample(sample_id, plot=False):
    machine_annotations = db.get_machine_annotations(sample_id)
    sample = db.get_sample_by_id(sample_id)
    image_filename = os.path.join(config.get_server_image_path(), sample['filename'])
    for machine_annotation in machine_annotations:
        heatmap_image_filename = os.path.join(config.get_server_heatmap_path(), machine_annotation['heatmap_image_filename'])
        heatmap_filename = os.path.join(config.get_server_heatmap_path(), machine_annotation['heatmap_filename'])
        #plot_heatmap(image_filename, heatmap_filename, heatmap_image_filename)
        print heatmap_image_filename
        heatmap_image = imread(heatmap_image_filename)
        positions = compute_stomata_positions(machine_annotation, heatmap_image, plot=plot)
        #db.update_machine_annotation_positions(machine_annotation['_id'], positions)
