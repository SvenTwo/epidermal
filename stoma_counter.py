#!/usr/bin/env python
# Count stomata from heatmap

import time
import os
from apply_fcn import load_latest_model, process_image_file, plot_heatmap
from config import config
import db
import numpy as np
import cv2
from bson.objectid import ObjectId
import matplotlib.pyplot as plt
from scipy.ndimage import imread

prob_threshold = 1.0
prob_area_threshold = 1.0

def compute_stomata_positions(machine_annotation, heatmap_image, plot=False):
    # Load heatmap + image
    heatmap_filename = os.path.join(config.server_heatmap_path, machine_annotation['heatmap_filename'])
    sample_info = db.get_sample_by_id(machine_annotation['sample_id'])
    # Derive zoom
    probs = np.load(heatmap_filename)
    margin = machine_annotation['margin']
    zoom = float(sample_info['size'][0] - 2 * margin) / probs.shape[0]
    pthresh = (probs > prob_threshold).astype(np.uint8).copy()
    all_contours = cv2.findContours(pthresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    large_contours = [c for c in all_contours if cv2.contourArea(c) > prob_area_threshold]
    positions = []

    for c in large_contours:
        (pos, radius) = cv2.minEnclosingCircle(c)
        pos_zoomed = tuple(int(x * zoom + margin + zoom/2) for x in pos)[::-1]
        radius_zoomed = int(radius * zoom)
        positions += [pos_zoomed]
        cv2.circle(heatmap_image, center=pos_zoomed, radius=radius_zoomed, color=(255,255,0), thickness=4)
    print 'Found %d stomata' % len(positions)
    if plot:
        f, axarr = plt.subplots(1, 3, figsize=(12, 7))
        axarr[0].matshow(probs)
        axarr[1].matshow(pthresh)
        axarr[2].imshow(heatmap_image)
        f.suptitle('%d Stomata' % len(positions))
        plt.show()
    return positions

def compute_stomata_positions_for_sample(sample_id, plot=False):
    machine_annotations = db.get_machine_annotations(sample_id)
    for machine_annotation in machine_annotations:
        heatmap_image_filename = os.path.join(config.server_heatmap_path, machine_annotation['heatmap_image_filename'])
        print heatmap_image_filename
        heatmap_image = imread(heatmap_image_filename)
        positions = compute_stomata_positions(machine_annotation, heatmap_image, plot=plot)
        db.update_machine_annotation_positions(machine_annotation['_id'], positions)


if __name__ == '__main__':
    compute_stomata_positions_for_sample(ObjectId('591731987ade9f7e7f856b0a'), plot=True)