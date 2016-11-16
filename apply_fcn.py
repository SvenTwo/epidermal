#!/usr/bin/env python
# Apply trained FCN to input file(s)

import os
import caffe
from paths import run_path, data_path
import matplotlib.pyplot as plt
import matplotlib.colors as plc
import numpy as np
import cv2

def load_model(run_name, iter, model_name, train_name, fc8_suffix, input_size):
    model_fn = os.path.join(run_path, run_name, 'out', train_name + '_iter_' + str(iter) + '_fcn.caffemodel')
    proto_fn_fcn = os.path.join(run_path, run_name, model_name + 'fcn.prototxt')
    caffe.set_mode_gpu()
    caffe.set_device(3)
    net = caffe.Net(proto_fn_fcn, caffe.TEST, weights=model_fn)
    net.blobs['data'].reshape(1, 3, input_size[1], input_size[0])
    # create transformer for the input called 'data'
    transformer = caffe.io.Transformer({'data': (1, 3, input_size[1], input_size[0])})
    transformer.set_transpose('data', (2, 0, 1))  # move image channels to outermost dimension
    transformer.set_mean('data', np.array((104, 117, 123)))  # subtract the dataset-mean value in each channel
    transformer.set_raw_scale('data', 255)  # rescale from [0, 1] to [0, 255]
    transformer.set_channel_swap('data', (2, 1, 0))  # swap channels from RGB to BGR
    output_name = 'fc8' + fc8_suffix + '-conv'
    return net, transformer, output_name

def process_image(net, transformer, output_name, image):
    transformed_image = transformer.preprocess('data', image)
    net.blobs['data'].data[0, ...] = transformed_image
    output = net.forward()
    probs = output[output_name][0]
    return np.transpose(probs[1,:,:])

def process_image_file(net, transformer, output_name, image_folder, heatmap_folder, image_filename):
    image = caffe.io.load_image(os.path.join(image_folder, image_filename))
    probs = process_image(net, transformer, output_name, image)
    out_filename = os.path.join(heatmap_folder, image_filename + '.npy')
    np.save(out_filename, probs)

def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.299, 0.587, 0.114])

def plot_heatmap(image_folder, heatmap_folder, image_filename):
    image = caffe.io.load_image(os.path.join(image_folder, image_filename))
    probs = np.load(os.path.join(heatmap_folder, image_filename + '.npy'))
    probs = probs.transpose()

    # Align probability map to input image
    grayimage = rgb2gray(image)
    stride = 32
    probs = cv2.resize(probs, (stride * probs.shape[1], stride * probs.shape[0]), interpolation=cv2.INTER_CUBIC)
    pad = [grayimage.shape[i] - probs.shape[i] for i in (0,1)]
    probs = cv2.copyMakeBorder(probs, pad[0]/2, (pad[0]+1)/2, pad[1]/2, (pad[1]+1)/2, cv2.BORDER_CONSTANT)

    # Rescale probs for hsv2rgb
    probs = np.clip(probs, 0, 10)
    probs /= np.max(probs.flatten())

    # Combine into one image
    hsv = plc.hsv_to_rgb(np.dstack((np.zeros(grayimage.shape), probs, grayimage)))

    plt.imsave(os.path.join(heatmap_folder, image_filename), hsv)
    #plt.imshow(hsv)
    #plt.show()

if __name__ == '__main__':
    run_name = 'epi1'
    iter = 2000
    model_name = 'alexnet'
    train_name = 'alexnetftc'
    fc8_suffix = 'stoma'
    input_size = (2048, 2048)
    image_folder = os.path.join(data_path, 'Pb_09_01_16_No_xy_Archive')
    heatmap_folder = os.path.join(data_path, 'epi_heatmaps')
    #image_filename = 'VT_DCK_09_R3_B_A1.jpg'

    net, transformer, output_name = load_model(run_name, iter, model_name, train_name, fc8_suffix, input_size)
    for image_filename in os.listdir(image_folder):
        if image_filename.lower().endswith('.jpg'):
            print ('%s...' % image_filename),
            process_image_file(net, transformer, output_name, image_folder, heatmap_folder, image_filename)
            plot_heatmap(image_folder, heatmap_folder, image_filename)
            print 'done.'
