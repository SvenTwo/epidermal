#!/usr/bin/env python
# Add missing image quality measures using PyImageQualityRanking to DB entries.

import os

import db
from config import config
from image_measures import get_image_measures


def add_image_measures():
    for s in db.samples.find({'processed': True}):
        if not s.get('imq_entropy'):
            image_filename = s['filename']
            print 'Processing %s...' % image_filename
            image_filename_full = os.path.join(config.get_server_image_path(), image_filename)
            image_measures = get_image_measures(image_filename_full)
            db.set_image_measures(s['_id'], image_measures)


if __name__ == '__main__':
    add_image_measures()
