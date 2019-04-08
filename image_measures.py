#!/usr/bin/env python
# Image quality measures using PyImageQualityRanking

try:
    from pyimq import filters, myimage, script_options
    has_pyimq = True
except ImportError:
    print 'Error importing pyimq. Image quality measures not available.'
    has_pyimq = False


if has_pyimq:
    options = script_options.get_quality_script_options([])


    image_measures = ['imq_entropy', 'imq_hf_mean', 'imq_hf_std', 'imq_hf_entropy', 'imq_hf_threshfreq', 'imq_hf_power',
                      'imq_hf_skewness', 'imq_hf_kurtosis']


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

else:
    image_measures = []

    def get_image_measures(image_filename):
        return {}
