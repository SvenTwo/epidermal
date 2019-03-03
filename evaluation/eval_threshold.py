#!/usr/bin/env python2.7
# Find optimal threshold on test set

import os
from bson import ObjectId
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from epidermal import db
from epidermal.config import config
from epidermal.stoma_counter import compute_stomata_positions_on_prob


net_name = 'alexnetftc_5000'
bins = np.arange(0, 4, 0.1)


def get_heatmap_fn(sample):
    basename, ext = os.path.splitext(sample['filename'])
    heatmap_filename = os.path.join(net_name, basename + '_heatmap.npz')
    heatmap_filename_full = os.path.join(config.server_heatmap_path, heatmap_filename)
    heatmap_image_filename = os.path.join(net_name, basename + '_heatmap.jpg')
    heatmap_image_filename_full = os.path.join(config.server_heatmap_path, heatmap_image_filename)
    return heatmap_filename_full

def test_on_dataset(model, dataset_id):
    ds = db.get_dataset_by_id(dataset_id)
    samples = list(db.get_samples(dataset_id=dataset_id))
    n = len(samples)
    n_bins = len(bins)
    npreds = np.zeros((n, n_bins, 2))
    for i_sample, sample in enumerate(tqdm(samples)):
        ma = db.get_machine_annotations(sample['_id'], model['_id'])[0]
        heatmap_fn = get_heatmap_fn(sample)
        hm = np.load(heatmap_fn)
        probs = hm['probs']
        gt = sample['human_position_count']
        for it, pthresh in enumerate(bins):
            pathresh = pthresh / 2.0
            pos = compute_stomata_positions_on_prob(probs=probs,
                                                    scale=hm['scale'],
                                                    margin=ma['margin'],
                                                    sample_size=sample['size'],
                                                    heatmap_image=None,
                                                    plot=False,
                                                    do_contour=False,
                                                    do_peaks=True,
                                                    prob_threshold=pthresh,
                                                    prob_area_threshold=pathresh,
                                                    verbose=False)
            npos = len(pos)
            npreds[i_sample, it, 0] = gt
            npreds[i_sample, it, 1] = npos
    return npreds


if __name__ == '__main__':
    npd = test_on_dataset(db.get_primary_model(), ObjectId('5a257e49bca3b71cfbb891c5'))
    np.save('/home/sven2/epicounttest.npy', npd)
    npd = np.load('/home/sven2/epicounttest.npy')
    err = np.abs(npd[:, :, 1] - npd[:, :, 0])
    merr = np.mean(err, axis=0)
    plt.plot(bins, merr)
    plt.ylim([0, 50])
    plt.show()
