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
    fig, ax = plt.subplots()
    test_ds_ids = {
        'twenty_x_test': '5a257e49bca3b71cfbb891c5',
        'stomata_patterning_1k': '5ca76766bca3b70d983849fe',
        'cuticle_db_test': '5a2c3f7cbca3b76969257209',
    }
    for tst_name, tst_id in test_ds_ids.iteritems():
        fname = '/home/sven2/epicounttest_%s.npy' % tst_name
        if os.path.isfile(fname):
            npd = np.load(fname)
        else:
            npd = test_on_dataset(db.get_primary_model(), ObjectId(tst_id))
            np.save(fname, npd)
        err = np.abs(npd[:, :, 1] - npd[:, :, 0])
        merr = np.mean(err, axis=0)
        ax.plot(bins, merr, label=tst_name)
    sbins = np.arange(0, 4, 0.5)
    sbins_vals = np.exp(sbins) / (np.exp(sbins) + np.exp(-sbins))
    sbin_strings = map(lambda v: '%.3f' % v, sbins_vals)
    ax.set_xticks(sbins)
    ax.set_xticklabels(sbin_strings, rotation=45)
    #ax.set_ylim([0, 27])
    ax.set_xlabel('Threshold probability')
    ax.set_ylabel('Error count')
    plt.legend()
    plt.tight_layout()
    plt.savefig('/home/sven2/epi_err_by_thresh.png')
    plt.show()
