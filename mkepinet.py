#!/usr/bin/env python
# Create model definition files
# (Requires serrelab changes to caffe)

from serrecaffe.model_defs.fcn import *
from serrecaffe.model_defs.solver import *
from serrecaffe.model_defs.def_fcn_model import alexnet, alexnet_fcn, save_train_val_files, save_net, ensure_run_folder, symlink_files
from paths import data_path

def make_alexnet_leaves_aa(name, run_name, debug, solver_mode, input_size, num_output, is_color, top_output_name, **kwargs):
    net = alexnet(name=name, input_size=input_size, num_output=num_output, is_color=is_color, top_output_name=top_output_name, **kwargs)
    for starting_weights, weight_suffix in [(None, 'scratch'), ('bvlc_reference_caffenet.caffemodel', 'ftc')]:
        save_train_val_files(net, run_name, solver_name=net.name + weight_suffix, debug=debug, solver_mode=solver_mode,
            weights_filename=starting_weights, test_interval=500, snapshot=500, max_iter=5000)
    fcnet = alexnet_fcn(name=name+'fcn', batch_size=1, input_size=[input_size,input_size], is_color=is_color, num_output=num_output, top_output_name=top_output_name)
    save_net(fcnet, fcnet.name + '.prototxt')

def mk_epinet_v1():
    debug = False
    solver_mode = 'GPU'
    run_name = 'epi1'
    train_db = 'epi1_train_lmdb'
    test_db = 'epi1_val_lmdb'

    ensure_run_folder(run_name, output_folder='/home/sven2/caffedata_cifs')
    symlink_files(data_path, '*_lmdb')
    symlink_files('/home/sven2/caffedata', 'bvlc_reference_caffenet.caffemodel')
    num_classes = 2

    defpars = dict(run_name=run_name, debug=debug, solver_mode=solver_mode, test_batch_size=1, is_color=True,
                   num_output=num_classes, top_output_name='stoma', train_db=train_db, test_db=test_db,
                   mean=[104, 117, 123])

    make_alexnet_leaves_aa(name='alexnet', batch_size=64, input_size=227, **defpars)

if __name__ == '__main__':
    mk_epinet_v1()