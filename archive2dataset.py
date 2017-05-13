#!/usr/bin/env python
# Generate a training dataset of stoma/non-stoma images from Karl's annotated images

import os
from config import config
import csv
from collections import defaultdict
import cv2
import numpy as np
from leaves.gen_filelist import split_train_test, save_filelist_shuffled
import db
import shutil
from PIL import Image
from datetime import strftime

def load_positions(filename):
    # Load position list formatted as rows with
    # id\tx\ty
    entries = list(csv.reader(open(filename, 'rt'), delimiter='\t'))
    positions = defaultdict(list)
    for entry in entries[1:]: # Start on second line to ignore header
        positions[entry[0]] += [[int(entry[1]), int(entry[2])]]
    return positions

def ensure_path_exists(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def get_sample_filename(pos, angle, extract_size, output_path, img_name):
    # Compose filename of sample from source and extraction position and rotation
    return os.path.join(output_path, '%s_%04d_%04d_%03d_%03d_%03d.jpg' % (img_name, pos[0], pos[1], int(angle), extract_size[0], extract_size[1]))

def extract_sample(img, pos, angle, output_path, img_name, extract_size):
    filename = get_sample_filename(pos, angle, extract_size, output_path, img_name)
    M = cv2.getRotationMatrix2D(tuple(pos), angle, 1)
    M[0, 2] -= pos[0] - extract_size[0] / 2
    M[1, 2] -= pos[1] - extract_size[1] / 2
    sample = cv2.warpAffine(img, M, extract_size)
    cv2.imwrite(filename, sample)
    print 'Extracted sample %s.' % filename

def extract_target_positions(img, allpos, output_path, img_name, angles, extract_size):
    # Extract all given positions at all angles
    ensure_path_exists(output_path)
    for pos in allpos:
        for angle in angles:
            extract_sample(img, pos, angle, output_path, img_name, extract_size)

def extract_distractor_positions(img, allpos, output_path, img_name, angles, extract_size):
    # Extract from positions not close to any given positions at all angles
    ensure_path_exists(output_path)
    n_distractors = len(allpos)
    size = img.shape
    min_margin = [c*3/2 for c in extract_size] # For now, only extract near the center because of unlabeled targets near the border
    min_dist = max(extract_size)
    max_retry = 100000
    while n_distractors and max_retry:
        # Find a random position in the image (or at its border) that is not close to any targets
        pos = [np.random.random_integers(min_margin[i], size[1-i]-min_margin[i]) for i in (0, 1)]
        # Make sure it's not close to any target position
        pos_ok = True
        for tpos in allpos:
            dist = np.linalg.norm([tpos[i] - pos[i] for i in (0, 1)])
            if dist < min_dist:
                pos_ok = False
                max_retry -= 1
                break
        if not pos_ok:
            continue
        # Sample here
        for angle in angles:
            extract_sample(img, pos, angle, output_path, img_name, extract_size)
        n_distractors -= 1

def extract_positions(img_filename, allpos, output_path, img_name, angles, extract_size):
    # Load image and extract both positive examples from pos as well as negative examples from elsewhere
    # Store images into output_path/target and output_path/distractor
    # Load image
    img = cv2.imread(img_filename)
    #for pos in allpos:
    #    cv2.circle(img, tuple(pos), 96, (255, 255, 0), thickness=1)
    #    cv2.circle(img, tuple(pos), 128, (255, 255, 0), thickness=3)
    #    cv2.circle(img, tuple(pos), 172, (127, 127, 0), thickness=3)
    # Extract positions
    extract_target_positions(img, allpos, os.path.join(output_path, 'target'), img_name, angles, extract_size)
    extract_distractor_positions(img, allpos, os.path.join(output_path, 'distractor'), img_name, angles, extract_size)

def plot_locations(img_filename, allpos, out_filename):
    # Put some red circles around the annotated locations
    # Load image
    img = cv2.imread(img_filename)
    for pos in allpos:
        cv2.circle(img, tuple(pos), 128, (255, 255, 0), thickness=3)
    cv2.imwrite(out_filename, img)
    print 'Wrote annotation to %s.' % out_filename

def plot_all_locations(train_path, positions, output_path):
    ensure_path_exists(output_path)
    for img_name, allpos in positions.iteritems():
        img_filename = os.path.join(train_path, img_name + '.jpg')
        plot_locations(img_filename, allpos, os.path.join(output_path, 'targets_' + img_name + '.jpg'))

# Iterate over all image files in subfolders of path and put them into the leaves dictionary by family
# Return number of leaves added
def generate_filelist_from_folder(filelists, path, img_root, category=None):
    valid_extensions = ['jpeg', 'jpg', 'png', 'tif', 'tiff']
    n = 0
    for filename in os.listdir(path):
        full_fn = os.path.join(path, filename)
        if os.path.isdir(full_fn):
            if category is None:
                n += generate_filelist_from_folder(filelists, full_fn, img_root=img_root, category=filename)
            else:
                print 'Skipping subfolder %s' % full_fn
            continue
        if os.stat(full_fn).st_size <= 10240:
            print 'Skipping %s: Too small.' % full_fn
            continue
        extension = full_fn.split('.')[-1].lower()
        if not extension in valid_extensions:
            print 'Filename %s has unknown extension.' % full_fn
            continue
        if category is None:
            print 'Filename %s has no category.' % full_fn
            continue
        filelists[category] += [os.path.relpath(full_fn, img_root)]
        n += 1
    return n

def generate_filelist(path, img_root):
    filelists = defaultdict(list)
    n = generate_filelist_from_folder(filelists, path, img_root)
    return filelists

def generate_image_patches(train_path, positions, output_path, angles, extract_size):
    n_total = 0
    for img_name, allpos in positions.iteritems():
        img_filename = os.path.join(train_path, img_name + '.jpg')
        if not os.path.isfile(img_filename):
            print 'Skipping missing file %s.' % img_filename
            continue
        n = len(allpos)
        n_total += n
        print '%02d samples in file %s.' % (n, img_filename)
        extract_positions(img_filename, allpos, output_path, img_name, angles, extract_size)
    print '%d samples total.' % n_total

def archive2dataset():
    extract_size = (256, 256) # wdt, hgt
    n_angles = 8
    angles = np.linspace(0, 360, num=n_angles, endpoint=False)
    train_path = os.path.join(config.data_path, 'Pb_stomata_09_03_16_Archive')
    positions = load_positions(os.path.join(train_path, 'VT_stomata_xy_trial_10_15_16.txt'))
    #plot_all_locations(train_path, positions, os.path.join(data_path, 'epi_targets'))
    output_path = os.path.join(config.data_path, 'epi1')
    #generate_image_patches(train_path, positions, output_path, angles, extract_size)
    # Generate dataset text files
    filelist = generate_filelist(output_path, config.data_path)
    class_indices = {'distractor': 0, 'target': 1}
    train, val, test = split_train_test(filelist, n_test=100, n_val=100)
    save_filelist_shuffled(train, class_indices, os.path.join(config.data_path, 'epi1_train.txt'))
    save_filelist_shuffled(val, class_indices, os.path.join(config.data_path, 'epi1_val.txt'))
    save_filelist_shuffled(test, class_indices, os.path.join(config.data_path, 'epi1_test.txt'))

def db2dataset():
    # All human annotations in DB converted to a training set
    print strftime('%Y%m%d')

def get_karl_dataset_id():
    name = 'Pb_stomata_09_03_16_Archive'
    ds = db.get_dataset_by_name(name)
    if ds is None:
        ds = db.add_dataset(name)
    return ds['_id']

def pos2db(p):
    return { 'x': p[0], 'y': p[1] }

def import_karl_labels():
    dataset_id = get_karl_dataset_id()
    train_path = os.path.join(config.data_path, 'Pb_stomata_09_03_16_Archive')
    positions = load_positions(os.path.join(train_path, 'VT_stomata_xy_trial_10_15_16.txt'))
    for fn, pos in positions.iteritems():
        pos_db = [pos2db(p) for p in pos]
        fnj = fn + '.jpg'
        fn_full = os.path.join(train_path, fnj)
        im = Image.open(fn_full)
        filename = os.path.basename(fnj)
        fn_target = os.path.join(config.server_image_path, filename)
        shutil.copyfile(fn_full, fn_target)
        sample = db.add_sample(os.path.basename(fn_target), size=im.size, dataset_id=dataset_id)
        sample_id = sample['_id']
        db.set_human_annotation(sample_id, db.get_default_user()['_id'], pos_db, margin=32)
        print 'http://0.0.0.0:9000/info/%s' % str(sample_id)

    print train_path
    print positions


if __name__ == '__main__':
    import_karl_labels()
    #db2dataset()