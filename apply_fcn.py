#!/usr/bin/env python
# Apply trained FCN to input file(s)

import os
import caffe
from config import config
import matplotlib.pyplot as plt
import matplotlib.colors as plc
import numpy as np
import cv2

def init_model_transformer(net):
    net.blobs['data'].reshape(1, 3, net.input_size[1], net.input_size[0])
    # create transformer for the input called 'data'
    transformer = caffe.io.Transformer({'data': (1, 3, net.input_size[1], net.input_size[0])})
    transformer.set_transpose('data', (2, 0, 1))  # move image channels to outermost dimension
    transformer.set_mean('data', np.array((104, 117, 123)))  # subtract the dataset-mean value in each channel
    transformer.set_raw_scale('data', 255)  # rescale from [0, 1] to [0, 255]
    transformer.set_channel_swap('data', (2, 1, 0))  # swap channels from RGB to BGR
    net.transformer = transformer
    return transformer

def load_model(run_name, iter, model_name, train_name, fc8_suffix, input_size):
    model_fn = os.path.join(config.run_path, run_name, 'out', train_name + '_iter_' + str(iter) + '_fcn.caffemodel')
    proto_fn_fcn = os.path.join(config.run_path, run_name, model_name + 'fcn.prototxt')
    caffe.set_mode_gpu()
    caffe.set_device(2)
    net = caffe.Net(proto_fn_fcn, caffe.TEST, weights=model_fn)
    net.blobs['data'].reshape(1, 3, input_size[1], input_size[0])
    net.input_size = input_size[:2]
    init_model_transformer(net)
    net.output_name = 'fc8' + fc8_suffix + '-conv'
    net.name = '%s_%s_%d' % (run_name, train_name, iter)
    net.margin = get_net_margin(net)
    net.stride = 32
    print 'Loaded net %s (margin %d)' % (net.name, net.margin)
    return net

def get_net_margin(net):
    # Determine margin of data not included in the FCN: Just call forward once and check the in/out size
    input_shape = net.blobs['data'].shape
    output = net.forward()
    output_shape = output[net.output_name].shape
    margin = (input_shape[2] - output_shape[2]*32)//2
    return margin

def process_image(net, image):
    image_shape = (image.shape[1], image.shape[0])
    print ('Processing image shaped %s' % str(image.shape)),
    min_size = net.margin * 2 + net.stride * 2
    if image_shape[0] < min_size or image_shape[1] < min_size:
        raise RuntimeError('Image too small (min size %dx%d pixels)' % (min_size, min_size))
    if net.input_size != image_shape:
        net.input_size = image_shape
        init_model_transformer(net)
    transformed_image = net.transformer.preprocess('data', image)
    net.blobs['data'].data[0, ...] = transformed_image
    output = net.forward()
    probs = output[net.output_name][0]
    print 'Done.'
    return np.transpose(probs[1,:,:])

def process_image_file(net, image_filename_full, heatmap_filename_full):
    image = caffe.io.load_image(image_filename_full)
    probs = process_image(net, image)
    np.save(heatmap_filename_full, probs)

def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.299, 0.587, 0.114])

def plot_heatmap(image_filename_full, heatmap_filename_full, heatmap_image_filename_full):
    image = caffe.io.load_image(image_filename_full)
    probs = np.load(heatmap_filename_full)
    probs = probs.transpose()

    # Align probability map to input image
    grayimage = rgb2gray(image)
    stride = 32
    probs = cv2.resize(probs, (stride * probs.shape[1], stride * probs.shape[0]), interpolation=cv2.INTER_CUBIC)
    pad = [grayimage.shape[i] - probs.shape[i] for i in (0,1)]
    probs = cv2.copyMakeBorder(probs, pad[0]/2, (pad[0]+1)/2, pad[1]/2, (pad[1]+1)/2, cv2.BORDER_CONSTANT)

    # Darken image in padded region
    grayimage[:(pad[0] / +2), :] /= 2.0
    grayimage[(pad[0] / -2):, :] /= 2.0
    grayimage[(pad[0] / +2):(pad[0] / -2), :(pad[1] / +2)] /= 2.0
    grayimage[(pad[0] / +2):(pad[0] / -2), (pad[1] / -2):] /= 2.0

    # Rescale probs for hsv2rgb
    probs = np.clip(probs, 0, 10)
    probs /= np.max(probs.flatten())

    # Combine into one image
    hsv = plc.hsv_to_rgb(np.dstack((np.zeros(grayimage.shape), probs, grayimage)))

    plt.imsave(heatmap_image_filename_full, hsv)
    #plt.imshow(hsv)
    #plt.show()

def load_latest_model():
    run_name = 'epi1'
    iter = 2000
    model_name = 'alexnet'
    train_name = 'alexnetftc'
    fc8_suffix = 'stoma'
    input_size = (2048, 2048)
    return load_model(run_name, iter, model_name, train_name, fc8_suffix, input_size)

if __name__ == '__main__':
    image_folder = os.path.join(config.data_path, 'Pb_09_01_16_No_xy_Archive')
    heatmap_folder = os.path.join(config.data_path, 'epi_heatmaps')
    #image_filename = 'VT_DCK_09_R3_B_A1.jpg'

    net = load_latest_model()
    for image_filename in os.listdir(image_folder):
        if image_filename.lower().endswith('.jpg'):
            print ('%s...' % image_filename),
            image_filename_full = os.path.join(image_folder, image_filename)
            heatmap_filename_full = os.path.join(heatmap_folder, image_filename + '.npy')
            heatmap_image_filename_full = os.path.join(heatmap_folder, image_filename)
            process_image_file(net, image_filename_full, heatmap_filename_full)
            plot_heatmap(image_filename_full, heatmap_filename_full, heatmap_image_filename_full)
            print 'done.'
