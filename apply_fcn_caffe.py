#!/usr/bin/env python
# Apply trained FCN to input file(s)

import caffe
import matplotlib.pyplot as plt
import matplotlib.colors as plc
import numpy as np
from scipy.ndimage import zoom
import cv2


max_image_size = 4096


def fc8_to_prob(v):
    return np.exp(v) / (np.exp(v) + np.exp(-v))


def prob_to_fc8(p):
    p = np.clip(p, 0.00001, 0.99999)
    return np.log(p/(1-p)) / 2


def init_model(model_fn, proto_fn_fcn, worker_gpu_index, net_output_name, input_size, network_name):
    if worker_gpu_index > 0:
        caffe.set_mode_gpu()
        caffe.set_device(worker_gpu_index)
    else:
        caffe.set_mode_cpu()
    net = caffe.Net(proto_fn_fcn, caffe.TEST, weights=model_fn)
    net.original_shape = list(net.blobs['data'].shape)
    net.blobs['data'].reshape(1, 3, input_size[1], input_size[0])
    net.input_size = input_size[:2]
    init_model_transformer(net)
    net.output_name = net_output_name
    net.name = network_name
    net.stride = 32
    net.margin = get_net_margin(net)
    print 'Loaded net %s (margin %d)' % (net.name, net.margin)
    return net


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


def get_net_margin(net):
    # Determine margin of data not included in the FCN: Just call forward once and check the in/out size
    input_shape = net.blobs['data'].shape
    output = net.forward()
    output_shape = output[net.output_name].shape
    margin = (input_shape[2] - output_shape[2]*net.stride)//2
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


def process_image_file(net, image_filename_full, heatmap_filename_full=None, crop=False, verbose=True, scales=None):
    image = caffe.io.load_image(image_filename_full)
    if verbose:
        print 'process_image_file %s shape %s' % (image_filename_full, image.shape)
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
    if scales is not None:
        assert not crop
        best_score = -np.inf
        probs = None
        for zscale in scales:
            print 'process_image_file scale', zscale
            if zscale > 1.0:
                if image.shape[0] * zscale > max_image_size or image.shape[1] * zscale > max_image_size:
                    continue
            if zscale == 1.0:
                zimage = image
            else:
                zimage = zoom(image, (zscale, zscale, 1))
            zprobs = process_image(net, zimage, allow_undersize=crop, verbose=verbose)
            score = np.percentile(np.reshape(zprobs, (-1,)), 0.95)
            if score > best_score:
                probs = zprobs
                scale = zscale
        if probs is None:
            raise RuntimeError('Image too large for this network (max %dx%d)' % ((int(max_image_size/scales[0]),)*2))
    else:
        if verbose:
            print 'process_image_file default scale (1.0)'
        probs = process_image(net, image, allow_undersize=crop, verbose=verbose)
        scale = 1.0
    if verbose:
        print ('Probs shape x%.1f = %s' % (scale, str(probs.shape))),
    output = {
        'probs': probs,
        'scale': scale,
        'input_shape': image.shape[:2],
    }
    if heatmap_filename_full:
        if verbose:
            print 'process_image_file saving heatmap'
        np.savez_compressed(heatmap_filename_full, probs=probs, scale=scale)
    if verbose:
        print 'process_image_file done %s' % image_filename_full
    return output


def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.299, 0.587, 0.114])

def plot_heatmap(image_filename_full, heatmap_filename_full, heatmap_image_filename_full):
    image = caffe.io.load_image(image_filename_full)
    data = np.load(heatmap_filename_full)
    probs = np.array(data['probs'])
    scale = float(data['scale'])
    print 'plot_heatmap %s %.1f' % (str(probs.shape), scale)
    probs = probs.transpose()

    # Align probability map to input image
    grayimage = rgb2gray(image)
    stride = int(round(32 / scale))
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

    if heatmap_image_filename_full is not None:
        plt.imsave(heatmap_image_filename_full, hsv)
    #plt.imshow(hsv)
    #plt.show()
    return hsv
