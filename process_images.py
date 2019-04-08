#!/usr/bin/env python
# CLI tool to count stomata on images and output results in a CSV file.

import os
import matplotlib.pyplot as plt
from tqdm import tqdm
import csv

from apply_fcn_caffe import init_model, process_image_file, plot_heatmap
from stoma_counter import compute_stomata_positions_on_prob, default_prob_threshold, default_prob_area_threshold
from image_measures import get_image_measures, image_measures


all_results_fields = ['image_filename', 'count', 'margin', 'scale', 'positions'] + image_measures


# Load network according to args
def load_net(args):
    return init_model(model_fn=args.weights_filename,
                      proto_fn_fcn=args.proto_filename,
                      worker_gpu_index=args.gpu_index,
                      net_output_name=args.cnn_top_layer_name,
                      input_size=(256, 256),  # input will be reshaped on first image
                      network_name=os.path.basename(args.weights_filename))


# Count stomata on one image, output heatmap file and and return results record
def process_image(net, image_path, args):
    # Prepare parameters
    heatmap_path = None
    heatmap_image_path = None
    margin = int(net.margin / args.scale)
    heatmap_image = None
    has_heatmap = (args.heatmap_output_path is not None)
    if has_heatmap:
        heatmap_path = os.path.join(args.heatmap_output_path, os.path.basename(image_path)) + '.npz'
        heatmap_image_path = os.path.join(args.heatmap_output_path, os.path.basename(image_path)) + '.heatmap.jpg'
    if args.verbose:
        print 'Processing %s (heatmap image file %s)' % (image_path, heatmap_image_path)

    result = {
        'image_filename': os.path.basename(image_path),
        'margin': margin,
        'scale': args.scale,
    }

    # Get image quality parameters
    if args.verbose:
        print 'Getting image quality features...'
    result.update(get_image_measures(image_path))

    # Process image through CNN
    if args.verbose:
        print 'Processing CNN...'
    data = process_image_file(net, image_path,
                              crop=False,
                              verbose=args.verbose,
                              scales=[args.scale],
                              heatmap_filename_full=heatmap_path)

    # Output probabilities onto heatmap
    if has_heatmap:
        if args.verbose:
            print 'Plotting heatmap...'
        heatmap_image = plot_heatmap(image_path, heatmap_path, None)

    # Count stomata
    if args.verbose:
        print 'Counting stomata...'
    positions = compute_stomata_positions_on_prob(probs=data['probs'],
                                                  scale=args.scale,
                                                  margin=margin,
                                                  sample_size=data['input_shape'][:2],
                                                  heatmap_image=heatmap_image,
                                                  plot=False,
                                                  do_contour=has_heatmap and args.plot_contours,
                                                  do_peaks=has_heatmap and not args.plot_no_peaks,
                                                  prob_threshold=args.prob_threshold,
                                                  prob_area_threshold=args.prob_area_threshold)
    result['count'] = len(positions)
    result['positions'] = positions
    if args.verbose:
        print '...found %d stomata.' % result['count']

    # Save heatmap
    if has_heatmap:
        if args.verbose:
            print 'Saving heatmap...'
        plt.imsave(heatmap_image_path, heatmap_image)

    if args.verbose:
        print '%s done.' % image_path

    return result


# Count stomata on a list of images
def process_images(net, image_paths, args):
    if not args.verbose:
        image_paths = tqdm(image_paths)
    return map(lambda p: process_image(net, p, args), image_paths)


# Output results
def write_results_to_file(results, output_filename, output_fields):
    with open(output_filename, 'wt') as fid:
        writer = csv.writer(fid, quoting=csv.QUOTE_MINIMAL)
        # Write header
        writer.writerow(output_fields)
        # Write results
        for result in results:
            writer.writerow(map(lambda f: result.get(f), output_fields))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='CLI tool to count stomata on images.')
    parser.add_argument('--weights-filename',
                        type=str,
                        required=True,
                        help='caffe weights file for processing CNN.')
    parser.add_argument('--proto-filename',
                        type=str,
                        required=True,
                        help='caffe CNN definition prototxt file.')
    parser.add_argument('--gpu-index',
                        type=int,
                        default=0,
                        help='Index of GPU to initialize caffe on. If -1, no GPU is used.')
    parser.add_argument('--cnn-top-layer-name',
                        type=str,
                        default='fc8stoma-conv',
                        help='CNN output layer to be used for probability maps. Note that by default, the fc8 top '
                             'layer (not the SoftMax on top) is expected to be used.')
    parser.add_argument('--scale',
                        type=float,
                        default=1.0,
                        help='Input scale. Larger values means the image is zoomed in (for smaller stomata).')
    parser.add_argument('--heatmap-output-path',
                        type=str,
                        help='If passed, probability maps are output into this folder both as numpy data files and as '
                             'images. Filenames are the basenames of all input files (without directory structure).')
    parser.add_argument('--plot-contours',
                        action='store_true',
                        help='Add contours to output heatmap images.')
    parser.add_argument('--plot-no-peaks',
                        action='store_true',
                        help='Do not mark detected stomata in output heatmap images.')
    parser.add_argument('--prob-threshold',
                        type=float,
                        default=default_prob_threshold,
                        help='Threshold to determine a stoma. Note that thresholds are applied to the CNN raw output '
                             'layer preceding softmax, so the softmax prob would be defined from this threshold p as '
                             'prob_thresh=exp(p)/(exp(p)+exp(-p)).')
    parser.add_argument('--prob-area-threshold',
                        type=float,
                        default=default_prob_area_threshold,
                        help='Threshold for countour area drawing if --plot-contours is passed.')
    parser.add_argument('--csv-output-filename',
                        type=str,
                        required=True,
                        help='CSV filename to output results into.')
    parser.add_argument('--output-fields',
                        type=str,
                        nargs='+',
                        default=all_results_fields,
                        choices=sorted(all_results_fields),
                        help='Which fields to save into the output CSV file. Defaults to all fields.')
    parser.add_argument('--verbose',
                        action='store_true',
                        help='Log some more outputs.')

    parser.add_argument('infiles',
                        metavar='image-paths',
                        type=str,
                        nargs='+',
                        help='Input image filenames.')

    arguments = parser.parse_args()

    # Init output path
    if arguments.heatmap_output_path is not None:
        try:
            os.makedirs(arguments.heatmap_output_path)
        except OSError:
            # Directory exists? That's OK
            if not os.path.isdir(arguments.heatmap_output_path):
                raise

    if arguments.verbose:
        print 'Loading CNN...'
    cnn = load_net(arguments)

    if arguments.verbose:
        print 'Processing %d images...' % len(arguments.infiles)
    result_records = process_images(cnn, arguments.infiles, arguments)

    if arguments.verbose:
        print 'Writing results to %s...' % arguments.csv_output_filename
    write_results_to_file(result_records, arguments.csv_output_filename, arguments.output_fields)
