#!/usr/bin/env python2.7
# Check for heatmaps and/or images that do not correspond to a sample and can be deleted.

import os
from collections import defaultdict

from epidermal import db
from epidermal.config import config


def basename_only(fn):
    return os.path.splitext(fn)[0]


def heatmap_basename_only(fn):
    return fn[:-len('_heatmap.jpg')]


if __name__ == '__main__':
    db_records = set()

    for sample in db.samples.find({}):
        fn = basename_only(sample['filename'])
        if fn in db_records:
            print 'Warning: Duplicate file', fn
        db_records.add(fn)

    basename_to_files = defaultdict(list)
    server_image_filenames = os.listdir(config.get_server_image_path())
    server_heatmap_filenames = os.listdir(config.get_server_heatmap_path() + '/alexnetftc_5000')
    for fn in server_image_filenames:
        basename_to_files[basename_only(fn)].append(os.path.join(config.get_server_image_path(), fn))
    for fn in server_heatmap_filenames:
        basename_to_files[heatmap_basename_only(fn)].append(os.path.join(config.get_server_heatmap_path(),
                                                                         'alexnetftc_5000', fn))
    server_images = set(map(basename_only, server_image_filenames))
    server_heatmaps = set(map(heatmap_basename_only, server_heatmap_filenames))
    server_files = server_images | server_heatmaps

    n_removed = 0
    for dead_img in server_files - db_records:
        for fn in basename_to_files[dead_img]:
            os.remove(fn)
            print 'Rm:', fn
            n_removed += 1

    print '%d images on server.' % len(server_images)
    print '%d heatmaps on server.' % len(server_heatmaps)
    print '%d DB records.' % len(db_records)
    print '%d DB records missing for image.' % len(server_images - db_records)
    print '%d DB records missing for heatmap.' % len(server_heatmaps - db_records)
    print '%d DB records missing for file.' % len(server_files - db_records)
    print '%d heatmap missing for image.' % len(server_images - server_heatmaps)
    print '%d images missing for heatmap.' % len(server_heatmaps - server_images)
    print '%d image missing for DB record.' % len(db_records - server_images)
    print '%d removed' % n_removed
