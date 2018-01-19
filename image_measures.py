#!/usr/bin/env python
# Image quality measures using PyImageQualityRanking

import os
from pyimq import filters, myimage, script_options
import db
from config import config


options = script_options.get_quality_script_options([])


def get_image_measures(image_filename):
    image = myimage.MyImage.get_generic_image(image_filename)
    # Green channel for rgb
    if image.is_rgb():
        image = image.get_channel(options.rgb_channel)
    print 'image.shape', image.images.shape
    task = filters.LocalImageQuality(image, options)
    task.set_smoothing_kernel_size(100)
    entropy = task.calculate_image_quality()
    task2 = filters.FrequencyQuality(image, options)
    finfo = task2.analyze_power_spectrum()
    result = {}
    result['imq_entropy'] = entropy
    result['imq_hf_mean'] = finfo[0]
    result['imq_hf_std'] = finfo[1]
    result['imq_hf_entropy'] = finfo[2]
    result['imq_hf_threshfreq'] = finfo[3]
    result['imq_hf_power'] = finfo[4]
    result['imq_hf_skewness'] = finfo[5]
    result['imq_hf_kurtosis'] = finfo[6]
    return result


# Fix stats where it's missing
def add_image_measures():
    for s in db.samples.find({'processed': True}):
        if not s.get('imq_entropy'):
            image_filename = s['filename']
            print 'Processing %s...' % image_filename
            image_filename_full = os.path.join(config.server_image_path, image_filename)
            image_measures = get_image_measures(image_filename_full)
            db.set_image_measures(s['_id'], image_measures)


if __name__ == '__main__':
    add_image_measures()
