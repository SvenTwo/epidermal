#!/usr/bin/env python
# FCN conversion. Convert a classification network into a per-pixel annotation model
# (I.e. AlexNet -> FCN8)
# # Adapted from http://nbviewer.ipython.org/github/BVLC/caffe/blob/master/examples/net_surgery.ipynb

import caffe
import os
import numpy as np
from paths import run_path

def convert_fcn(run_name, iter, model_name, train_name, fc_suffix, fc8_suffix, flatten_grayscale):
    os.chdir(os.path.join(run_path, run_name))
    model_fn = os.path.join(run_path, run_name, 'out', train_name + '_iter_' + str(iter) + '.caffemodel')
    proto_fn_orig = os.path.join(run_path, run_name, model_name + '.prototxt')
    proto_fn_fcn = os.path.join(run_path, run_name, model_name + 'fcn.prototxt')

    # Load the original network and extract the fully connected layers' parameters.
    net = caffe.Net(proto_fn_orig, caffe.TEST, weights=model_fn)
    params = ['fc6' + fc_suffix, 'fc7' + fc_suffix, 'fc8-' + fc8_suffix]
    fc_params = {pr: (net.params[pr][0].data, net.params[pr][1].data) for pr in params}

    # Load the fully convolutional network to transplant the parameters.
    net_full_conv = caffe.Net(proto_fn_fcn, caffe.TEST, weights=model_fn)
    params_full_conv = ['fc6-conv', 'fc7-conv', 'fc8' + fc8_suffix + '-conv']
    # conv_params = {name: (weights, biases)}
    conv_params = {pr: (net_full_conv.params[pr][0].data, net_full_conv.params[pr][1].data) for pr in params_full_conv}

    for fc in params:
        print 'ORIG {} weights are {} dimensional and biases are {} dimensional'.format(fc, fc_params[fc][0].shape,
                                                                                        fc_params[fc][1].shape)

    for conv in params_full_conv:
        print 'FCN {} weights are {} dimensional and biases are {} dimensional'.format(conv, conv_params[conv][0].shape,
                                                                                       conv_params[conv][1].shape)

    for pr, pr_conv in zip(params, params_full_conv):
        conv_params[pr_conv][0].flat = fc_params[pr][0].flat  # flat unrolls the arrays
        conv_params[pr_conv][1][...] = fc_params[pr][1]

    if flatten_grayscale:
        conv1_weight = net.params['conv1'][0].data
        conv1_bias = net.params['conv1'][1].data
        net_full_conv.params['conv1g'][0].data[...] = np.sum(conv1_weight, axis=1, keepdims=True)
        net_full_conv.params['conv1g'][1].data[...] = conv1_bias

    out_fn = os.path.join(run_path, run_name, 'out', train_name + '_iter_' + str(iter) + '_fcn.caffemodel')
    print 'saving to ', out_fn
    net_full_conv.save(out_fn)

def convert_epi1():
    run_name = 'epi1'
    iter = 2000
    model_name = 'alexnet'
    train_name = 'alexnetftc'
    fc_suffix = ''
    fc8_suffix = 'stoma'
    flatten_grayscale = False
    convert_fcn(run_name, iter, model_name, train_name, fc_suffix, fc8_suffix, flatten_grayscale)

if __name__ == '__main__':
    convert_epi1()