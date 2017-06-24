#!/usr/bin/env python2
# Retrain the Stomata identifier CNN

import os
from config import config
import subprocess
from archive2dataset import gen_new_output_path, db2patches, patches2filelist
from convert_model_to_fcn import convert_epi1
from worker import send_restart_signal

def imagelist2lmdb(image_root, imagelist_filename, lmdb_filename):
    print 'imagelist2lmdb to %s' % lmdb_filename
    if os.path.exists(lmdb_filename):
        print 'Exists. Skipping.'
        return
    cnv_cmd = os.path.join(config.caffe_path, 'tools', 'convert_imageset')
    cmd = [cnv_cmd, image_root + '/', imagelist_filename, lmdb_filename]
    if subprocess.call(cmd):
        raise RuntimeError('Error generating LMDB.')
    print 'LMDB created at %s' % lmdb_filename

def retrain(output_path=None):
    # Prepare data
    exec_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cnn'))
    if output_path is None:
        output_path = gen_new_output_path()
        db2patches(output_path)
        patches2filelist(output_path)
    for dset in ('train', 'val', 'test'):
        imagelist_filename = os.path.join(output_path, dset + '.txt')
        lmdb_filename =  os.path.join(output_path, dset + '_lmdb')
        imagelist2lmdb(output_path, imagelist_filename, lmdb_filename)
        exec_lmdb_filename = os.path.join(exec_path, dset + '_lmdb')
        if os.path.islink(exec_lmdb_filename):
            os.remove(exec_lmdb_filename)
        os.symlink(lmdb_filename, exec_lmdb_filename)
    # Prepare folder for processing
    os.chdir(exec_path)
    cnn_output_path = os.path.join(exec_path, 'out')
    if os.path.islink(cnn_output_path):
        os.remove(cnn_output_path)
    real_cnn_output_path = os.path.join(output_path, 'cnn')
    if not os.path.isdir(real_cnn_output_path):
        os.makedirs(real_cnn_output_path)
    print 'Link %s to %s' % (real_cnn_output_path, cnn_output_path)
    os.symlink(real_cnn_output_path, cnn_output_path)
    # Run caffe!
    caffe_cmd = os.path.join(config.caffe_path, 'tools', 'caffe')
    cmd = [caffe_cmd, 'train', '--solver', 'solver_alexnetftc.prototxt', '--weights', config.caffe_train_baseweights] + config.caffe_train_options.split(' ')
    print cmd
    if subprocess.call(cmd):
        raise RuntimeError('Error calling caffe.')

retrain_signal_filename = os.path.join(config.src_path, 'retraining.signal')
retrain_log_filename = os.path.join(config.src_path, 'cnn', 'retrain.log')

def is_network_retrain_running():
    return os.path.isfile(retrain_signal_filename)

def launch_network_retrain():
    subprocess.call(['touch', retrain_signal_filename])
    retrain_cmd = os.path.join(config.src_path, 'retrain_network.py')
    cmd = [retrain_cmd, '>' + retrain_log_filename, '2>&1 &']
    os.system(' '.join(cmd))

if __name__ == '__main__':
    #retrain('/media/data/epidermal/DS_2017_06_24_15_40')
    retrain()
    convert_epi1()
    # Restart worker process
    send_restart_signal()
    # Retrain done
    os.remove(retrain_signal_filename)
