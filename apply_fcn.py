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


def load_model(iter, model_name, train_name, fc8_suffix, input_size, model_id):
    basename = train_name + '_iter_' + str(iter) + '_fcn.caffemodel'
    #model_fn = os.path.join(config.src_path, 'cnn', 'out', train_name + '_iter_' + str(iter) + '_fcn.caffemodel')
    model_fn = os.path.join(config.src_path, 'cnn', str(model_id), 'out', basename)
    proto_fn_fcn = os.path.join(config.src_path, 'cnn', model_name + 'fcn.prototxt')
    caffe.set_mode_gpu()
    caffe.set_device(config.worker_gpu_index)
    net = caffe.Net(proto_fn_fcn, caffe.TEST, weights=model_fn)
    net.original_shape = list(net.blobs['data'].shape)
    net.blobs['data'].reshape(1, 3, input_size[1], input_size[0])
    net.input_size = input_size[:2]
    init_model_transformer(net)
    net.output_name = 'fc8' + fc8_suffix + '-conv'
    net.name = '%s_%d' % (train_name, iter)
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


def process_image(net, image, allow_undersize=False, verbose=True):
    image_shape = (image.shape[1], image.shape[0])
    min_size = net.margin * 2 + net.stride * 2
    if verbose:
        print ('Processing image shaped %s' % str(image.shape)),
    if not allow_undersize:
        if image_shape[0] < min_size or image_shape[1] < min_size:
            raise RuntimeError('Image too small (min size %dx%d pixels)' % (min_size, min_size))
    if net.input_size != image_shape:
        net.input_size = image_shape
        init_model_transformer(net)
    transformed_image = net.transformer.preprocess('data', image)
    net.blobs['data'].data[0, ...] = transformed_image
    output = net.forward()
    probs = output[net.output_name][0]
    if verbose:
        print 'Done.'
    return np.transpose(probs[1,:,:])


def process_image_file(net, image_filename_full, heatmap_filename_full=None, crop=False, verbose=True):
    image = caffe.io.load_image(image_filename_full)
    if crop:
        h, w = net.original_shape[2:4]
        if image.shape[0] > h:
            y0 = (image.shape[0] - h) // 2
            y1 = y0 + h
        else:
            y0 = 0
            y1 = image.shape[0]
        if image.shape[1] > w:
            x0 = (image.shape[1] - w) // 2
            x1 = x0 + w
        else:
            x0 = 0
            x1 = image.shape[1]
        image = image[y0:y1,x0:x1,:]
    probs = process_image(net, image, allow_undersize=crop, verbose=verbose)
    if verbose:
        print ('Probs shape %s' % str(probs.shape)),
    if heatmap_filename_full:
        np.save(heatmap_filename_full, probs)
    else:
        return probs


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


def load_model_by_record(model):
    iter = 5000
    model_name = 'alexnet'
    train_name = 'alexnetftc'
    fc8_suffix = 'stoma'
    input_size = (2048, 2048)
    return load_model(iter, model_name, train_name, fc8_suffix, input_size, model_id=model['_id'])
