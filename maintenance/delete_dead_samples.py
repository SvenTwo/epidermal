#!/usr/bin/env python2.7
# Check for heatmaps and/or images that do not correspond to a sample and can be deleted.

import os

from epidermal import db
from epidermal.config import config


def basename_only(fn):
    return os.path.splitext(fn)[0]


def heatmap_basename_only(fn):
    return fn[:-len('_heatmap.jpg')]


if __name__ == '__main__':
    print 'Not deleted', db.datasets.count({'deleted': False})
    deleted_datasets = db.datasets.find({'deleted': True})
    del_ids = map(lambda db: db['_id'], deleted_datasets)
    all_datasets = db.datasets.find({})
    all_ids = map(lambda db: db['_id'], all_datasets)
    print 'Deleted datasets', len(del_ids)
    del_samples = db.samples.count({'dataset_id': {'$in': del_ids}})
    other_samples = db.samples.count({'dataset_id': {'$nin': del_ids}})
    unknown_samples = db.samples.count({'dataset_id': {'$nin': all_ids}})
    print 'Deleted samples', del_samples
    print 'Other samples', other_samples
    print 'Unknown samples', unknown_samples
    db.samples.delete_many({'dataset_id': {'$in': del_ids}})
    db.datasets.delete_many({'deleted': True})
