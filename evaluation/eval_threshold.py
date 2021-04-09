#!/usr/bin/env python2.7
# Find optimal threshold on test set

import os
from bson import ObjectId
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tqdm import tqdm

from epidermal import db
from epidermal.config import config
from epidermal.stoma_counter import compute_stomata_positions_on_prob


def get_heatmap_fn(model, sample):
    net_name = 'alexnetftc_5000'
    #net_name = model['name']
    basename, ext = os.path.splitext(sample['filename'])
    heatmap_filename = os.path.join(net_name, basename + '_heatmap.npz')
    heatmap_filename_full = os.path.join(config.get_server_heatmap_path(), heatmap_filename)
    #heatmap_image_filename = os.path.join(net_name, basename + '_heatmap.jpg')
    #heatmap_image_filename_full = os.path.join(config.get_server_heatmap_path(), heatmap_image_filename)
    return heatmap_filename_full

def test_on_dataset(model, dataset_id, bins):
    samples = list(db.get_samples(dataset_id=dataset_id))
    n = len(samples)
    n_bins = len(bins)
    npreds = []
    for i_sample, sample in enumerate(tqdm(samples)):
        ma = db.get_machine_annotations(sample['_id'], model['_id'])[0]
        heatmap_fn = get_heatmap_fn(model, sample)
        hm = np.load(heatmap_fn)
        probs = hm['probs']
        gt = sample.get('human_position_count')
        if gt is None:
            continue
        npred = []
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
            npred.append([gt, npos])
        npreds.append(npred)
    return np.asarray(npreds)


def plot_err_by_threshold(model, dataset_ids, bins=None, use_cache=False):
    if bins is None:
        bins = np.arange(0, 4, 0.1)
    fig, ax = plt.subplots()
    for dataset_id in dataset_ids:
        ds = db.get_dataset_by_id(dataset_id)
        fname = os.path.join(config.get_data_path(), 'epicounttest_%s.npy' % str(dataset_id))
        if use_cache and os.path.isfile(fname):
            npd = np.load(fname)
        else:
            npd = test_on_dataset(model, dataset_id, bins=bins)
            if use_cache:
                np.save(fname, npd)
        err = np.abs(npd[:, :, 1] - npd[:, :, 0])
        merr = np.mean(err, axis=0)
        ax.plot(bins, merr, label=ds['name'])
    sbins = np.arange(bins[0], bins[-1], 0.5)
    sbins_vals = np.exp(sbins) / (np.exp(sbins) + np.exp(-sbins))
    sbin_strings = map(lambda v: '%.3f' % v, sbins_vals)
    ax.set_xticks(sbins)
    ax.set_xticklabels(sbin_strings, rotation=45)
    #ax.set_ylim([0, 27])
    ax.set_xlabel('Threshold probability')
    ax.set_ylabel('Error count')
    plt.legend()
    plt.tight_layout()


if __name__ == '__main__':
    test_ds_ids = [ObjectId('5a2c3f7cbca3b76969257209'),
                   ObjectId('5a257e49bca3b71cfbb891c5'),
                   ObjectId('5a2579fabca3b71b2cfb26db'),
                   ObjectId('5a2c1d47bca3b76459025490')]
    plot_err_by_threshold(db.get_primary_model(), test_ds_ids, use_cache=True)
    plt.savefig('/home/sven2/epi_err_by_thresh_db4.pdf')
    plt.savefig('/home/sven2/epi_err_by_thresh_db4.png')
    plt.show()
