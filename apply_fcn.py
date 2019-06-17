#!/usr/bin/env python
# Apply trained FCN to input file(s)

import os

from config import config
from apply_fcn_caffe import init_model


def load_model(iter, model_name, train_name, fc8_suffix, input_size, model_id):
    basename = train_name + '_iter_' + str(iter) + '_fcn.caffemodel'
    #model_fn = os.path.join(config.src_path, 'cnn', 'out', train_name + '_iter_' + str(iter) + '_fcn.caffemodel')
    model_fn = os.path.join(config.get_cnn_path(), str(model_id), 'out', basename)
    proto_fn_fcn = os.path.join(config.get_cnn_path(), model_name + 'fcn.prototxt')
    network_name = '%s_%d' % (train_name, iter)
    net = init_model(model_fn=model_fn,
                     proto_fn_fcn=proto_fn_fcn,
                     worker_gpu_index=config.worker_gpu_index,
                     net_output_name='fc8' + fc8_suffix + '-conv',
                     input_size=input_size,
                     network_name=network_name)
    return net


def load_model_by_record(model):
    iter = 5000
    model_name = 'alexnet'
    train_name = 'alexnetftc'
    fc8_suffix = 'stoma'
    input_size = (2048, 2048)
    return load_model(iter, model_name, train_name, fc8_suffix, input_size, model_id=model['_id'])
