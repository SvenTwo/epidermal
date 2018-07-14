#!/usr/bin/env python
# Count stomata from heatmap

import time
import os
from config import config
import db
import numpy as np
import cv2
from bson.objectid import ObjectId
import matplotlib.pyplot as plt
from scipy.ndimage import imread
from scipy.ndimage.filters import maximum_filter
from scipy.ndimage.morphology import generate_binary_structure, binary_erosion


prob_threshold = 2.0
prob_area_threshold = 1.0


def detect_peaks(image):
    """
    Takes an image and detect the peaks usingthe local maximum filter.
    Returns a boolean mask of the peaks (i.e. 1 when
    the pixel's value is the neighborhood maximum, 0 otherwise)
    http://stackoverflow.com/questions/3684484/peak-detection-in-a-2d-array
    """

    # define an 8-connected neighborhood
    neighborhood = generate_binary_structure(2,2)

    #apply the local maximum filter; all pixel of maximal value
    #in their neighborhood are set to 1
    local_max = maximum_filter(image, footprint=neighborhood)==image
    #local_max is a mask that contains the peaks we are
    #looking for, but also the background.
    #In order to isolate the peaks we must remove the background from the mask.

    #we create the mask of the background
    background = (image==0)

    #a little technicality: we must erode the background in order to
    #successfully subtract it form local_max, otherwise a line will
    #appear along the background border (artifact of the local maximum filter)
    eroded_background = binary_erosion(background, structure=neighborhood, border_value=1)

    #we obtain the final mask, containing only peaks,
    #by removing the background from the local_max mask (xor operation)
    detected_peaks = local_max ^ eroded_background

    return detected_peaks


def compute_stomata_positions(machine_annotation, heatmap_image, plot=False, do_contour=False, do_peaks=True):
    # Load heatmap + image
    heatmap_filename = os.path.join(config.server_heatmap_path, machine_annotation['heatmap_filename'])
    sample_info = db.get_sample_by_id(machine_annotation['sample_id'])
    # Derive zoom
    data = np.load(heatmap_filename)
    probs = data['probs']
    scale = data['scale']
    margin = machine_annotation['margin']
    zoom = float(sample_info['size'][0] - 2 * margin) / probs.shape[0]
    positions = []

    if do_contour and do_peaks:
        heatmap_image2 = np.copy(heatmap_image)
    else:
        heatmap_image2 = heatmap_image

    if do_peaks:
        probs_threshed = probs.copy()
        probs_threshed[probs < prob_threshold] = 0.0
        peaks = detect_peaks(probs_threshed)
        peak_coords = np.nonzero(peaks)
        for c in zip(peak_coords[0], peak_coords[1]):
            thresh = probs[c[0], c[1]]
            thresh_p = np.exp(thresh) / (np.exp(thresh) + np.exp(-thresh))
            pos = c
            radius = 3
            pos_zoomed = tuple(int(x * zoom + margin + zoom / 2) for x in pos)
            radius_zoomed = int(radius * zoom)
            positions += [pos_zoomed]
            cv2.circle(heatmap_image2, center=pos_zoomed, radius=radius_zoomed, color=(255, 255, 0), thickness=4)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(heatmap_image2, '%.3f' % thresh_p, pos_zoomed, font, 1.0, (127, 255, 0), 2, cv2.LINE_AA)

    if do_contour:
        pthresh = (probs >= prob_threshold).astype(np.uint8).copy()
        all_contours = cv2.findContours(pthresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        large_contours = [c for c in all_contours if cv2.contourArea(c) > prob_area_threshold]
        for c in large_contours:
            (pos, radius) = cv2.minEnclosingCircle(c)
            pos_zoomed = tuple(int(x * zoom + margin + zoom/2) for x in pos)[::-1]
            radius_zoomed = int(radius * zoom)
            positions += [pos_zoomed]
            cv2.circle(heatmap_image, center=pos_zoomed, radius=radius_zoomed, color=(255,255,0), thickness=4)

    print 'Found %d stomata' % len(positions)

    if plot:
        f, axarr = plt.subplots(2, 3, figsize=(12, 7))
        if do_contour:
            axarr[0,0].matshow(probs)
            axarr[0,1].matshow(pthresh)
            axarr[0,2].imshow(heatmap_image.transpose((1, 0, 2)))
        if do_peaks:
            axarr[1,0].matshow(probs_threshed)
            axarr[1,1].matshow(peaks)
            axarr[1, 2].imshow(heatmap_image2.transpose((1, 0, 2)))
        f.suptitle('%d Stomata' % len(positions))
        plt.figure()
        plt.imshow(heatmap_image2)
        plt.show()
    return positions


def compute_stomata_positions_for_sample(sample_id, plot=False):
    machine_annotations = db.get_machine_annotations(sample_id)
    sample = db.get_sample_by_id(sample_id)
    image_filename = os.path.join(config.server_image_path, sample['filename'])
    for machine_annotation in machine_annotations:
        heatmap_image_filename = os.path.join(config.server_heatmap_path, machine_annotation['heatmap_image_filename'])
        heatmap_filename = os.path.join(config.server_heatmap_path, machine_annotation['heatmap_filename'])
        #plot_heatmap(image_filename, heatmap_filename, heatmap_image_filename)
        print heatmap_image_filename
        heatmap_image = imread(heatmap_image_filename)
        positions = compute_stomata_positions(machine_annotation, heatmap_image, plot=plot)
        #db.update_machine_annotation_positions(machine_annotation['_id'], positions)


if __name__ == '__main__':
    compute_stomata_positions_for_sample(ObjectId('591797af7ade9f2afb56f254'), plot=True)