#!/usr/bin/env python
# Count stomata from heatmap

import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage.filters import maximum_filter
from scipy.ndimage.morphology import generate_binary_structure, binary_erosion


default_prob_threshold = 2.0
default_prob_area_threshold = 1.0


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


def compute_stomata_positions_on_prob(probs, scale, margin, sample_size,
                                      heatmap_image=None,
                                      plot=False, do_contour=False, do_peaks=True,
                                      prob_threshold=default_prob_threshold,
                                      prob_area_threshold=default_prob_area_threshold,
                                      verbose=True):
    zoom = float(sample_size[0] - 2 * margin) / probs.shape[0]
    if verbose:
        print 'Stomata count sample_size=%s  probs.shape=%s  zoom=%s' \
              % (sample_size, probs.shape, zoom)
    positions = []

    if do_contour and do_peaks and (heatmap_image is not None):
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
            if heatmap_image2 is not None:
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
            if heatmap_image is not None:
                cv2.circle(heatmap_image, center=pos_zoomed, radius=radius_zoomed, color=(255,255,0), thickness=4)

    if verbose:
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
