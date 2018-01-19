#!/usr/bin/env python
# Image sample database. DB is connected on module import

import numpy as np
import pymongo
from config import config
from hopkins import hopkins
from datetime import datetime


client = pymongo.MongoClient(host=config.db_address, port=config.db_port)
epidermal_db = client.epidermal


# Datasets #
############
datasets = epidermal_db['datasets']
samples = epidermal_db['samples']

# 'name' (str): Name to identify the dataset


def get_dataset_info(s):
    # Add sample counts for dataset
    if s is not None:
        s['sample_count'] = samples.count({'dataset_id': s['_id']})
        user_id = s.get('user_id')
        s['user'] = None if user_id is None else get_user_by_id(user_id)
    return s


def get_datasets(deleted=False):
    return [get_dataset_info(s) for s in datasets.find({'deleted': deleted})]


def get_datasets_by_user(user_id):
    return [get_dataset_info(s) for s in datasets.find({'deleted': False, 'user_id': user_id})]


def get_dataset_by_id(dataset_id):
    return get_dataset_info(datasets.find_one({'_id': dataset_id}))


def get_dataset_by_name(dataset_name, deleted=False):
    return get_dataset_info(datasets.find_one({'name': dataset_name, 'deleted': deleted}))


def get_example_dataset():
    return get_dataset_info(datasets.find_one({ 'tags': { '$in': ["examples"] }, 'deleted': False }))


def is_readonly_dataset(dataset):
    return "examples" in dataset['tags']


def is_readonly_dataset_id(dataset_id):
    return is_readonly_dataset(get_dataset_by_id(dataset_id))


def add_dataset(name, user_id=None):
    dataset_record = {'name': name, 'deleted': False, 'date_added': datetime.now(), 'tags': [], 'user_id': user_id}
    dataset_record['_id'] = datasets.insert_one(dataset_record).inserted_id
    return dataset_record


def delete_dataset(dataset_id):
    datasets.update({'_id': dataset_id}, {"$set": {'deleted': True}}, upsert=False)


def update_dataset_human_annotations(dataset_id):
    annotated_count = samples.count({'dataset_id': dataset_id, 'human_position_count': {'$gt': 0}})
    datasets.update({'_id': dataset_id}, {"$set": {'human_annotation_count': annotated_count}}, upsert=False)


def add_dataset_tag(dataset_id, new_tag):
    datasets.update({'_id': dataset_id}, {"$push": {'tags': new_tag}}, upsert=False)


def remove_dataset_tag(dataset_id, tag_name):
    datasets.update({'_id': dataset_id}, {"$pull": {'tags': tag_name}}, upsert=False)


def set_dataset_user(dataset_id, user_id):
    datasets.update({'_id': dataset_id}, {"$set": {'user_id': user_id}}, upsert=False)


# Fix dataset date added where it's missing
def fix_dataset_date_added():
    for d in datasets.find({'date_added': None}):
        print 'Updating ', d
        datasets.update({'_id': d['_id']}, {"$set": {'date_added': datetime.now()}}, upsert=False)


# Fix dataset human annotation count where it's missing
def fix_dataset_human_annotation_count():
    for d in datasets.find({'human_annotation_count': None}):
        print 'Updating ', d
        update_dataset_human_annotations(d['_id'])


# Fix datasets to have an empty tag array
def fix_dataset_tags():
    for d in datasets.find({'tags': None}):
        datasets.update({'_id': d['_id']}, {"$set": {'tags': []}}, upsert=False)


# Samples #
###########
# 'filename' (str): Filename (without path) of image
# 'dataset_id' (id): Parent dataset
# 'processed' (bool): Whether it has been processed by at least one model
# 'annotated' (bool): Whether it has been annotated by at least one human
# 'error' (bool): Could not process?
# 'error_string' (str): Error string if there was a problem with the sample
# 'size': array[2]: Image size [px]


def get_unprocessed_samples(dataset_id=None):
    query = {'processed': False, 'error': False}
    if dataset_id is not None:
        query['dataset_id'] = dataset_id
    return list(samples.find(query))


def get_processed_samples(dataset_id=None):
    query = {'processed': True, 'error': False}
    if dataset_id is not None:
        query['dataset_id'] = dataset_id
    return sorted(list(samples.find(query)), key=lambda x: x['name'])


def get_human_annotated_samples(dataset_id=None, train_label=None):
    if train_label is not None:
        result = []
        for dataset in datasets.find({'tags': {'$in': [train_label]}, 'deleted': False}):
            result += get_human_annotated_samples(dataset_id=dataset['_id'])
    else:
        query = {'annotated': True}
        if dataset_id is not None:
            query['dataset_id'] = dataset_id
        result = list(samples.find(query))
    return result


def get_human_unannotated_samples(dataset_id=None):
    query = {'annotated': False}
    if dataset_id is not None:
        query['dataset_id'] = dataset_id
    return list(samples.find(query))


def get_samples(dataset_id=None):
    query = {}
    if dataset_id is not None:
        query['dataset_id'] = dataset_id
    return sorted(list(samples.find(query)), key=lambda x: x['name'])


# Get next sample in dataset, starting from prev_sample_id
# If annotated is not None, it is used as a filter for possible next samples
# If there is no next sample (or it would be identical to prev_sample_id), return None
def get_next_sample_id(dataset_id, prev_sample_id, annotated=None, reverse_direction=False):
    sorted_samples = sorted(get_samples(dataset_id), key=lambda x: x['name'], reverse=reverse_direction)
    scnt = len(sorted_samples)
    sidx = [s['_id'] for s in sorted_samples].index(prev_sample_id)
    sidx_next = (sidx + 1) % scnt
    while sidx_next != sidx:
        if (annotated is None) or (sorted_samples[sidx_next]['annotated'] == annotated):
            break
        sidx_next = (sidx_next + 1) % scnt
    # Nothing found (only one sample in set or nothing with given annotation status)
    if sidx_next == sidx:
        return None
    # Sample found. Return its ID.
    return sorted_samples[sidx_next]['_id']


# Get index of given sample in dataset
def get_sample_index(dataset_id, sample_id):
    sorted_samples = sorted(get_samples(dataset_id), key=lambda x: x['name'])
    index = [s['_id'] for s in sorted_samples].index(sample_id)
    sample_count = len(sorted_samples)
    prev_index = (index - 1) if index else sample_count - 1
    next_index = (index + 1) % sample_count
    return index, sample_count, sorted_samples[prev_index]['_id'], sorted_samples[next_index]['_id']


def get_error_samples(dataset_id=None):
    query = {'error': True}
    if dataset_id is not None:
        query['dataset_id'] = dataset_id
    return list(samples.find(query))


def add_sample(name, filename, size, dataset_id=None):
    sample_record = {'name': name, 'filename': filename, 'dataset_id': dataset_id, 'size': size, 'processed': False,
                     'annotated': False, 'error': False, 'error_string': None, 'date_added': datetime.now()}
    sample_record['_id'] = samples.insert_one(sample_record).inserted_id
    return sample_record


def set_sample_data(sample_id, image_size):
    samples.update({'_id': sample_id}, {"$set": {'size': image_size}}, upsert=False)


def set_sample_error(sample_id, error_string):
    print 'Sample %s error: %s' % (str(sample_id), error_string)
    samples.update({'_id': sample_id}, {"$set": {'error': True, 'error_string': error_string}}, upsert=False)


def get_sample_by_id(sample_id):
    return samples.find_one({'_id': sample_id})


def delete_sample(sample_id):
    r = samples.delete_one({'_id': sample_id})
    return r.deleted_count == 1


def get_sample_count():
    return samples.count()


def fix_default_sample_names():
    # Set name=filename for all samples without name
    for s in samples.find({}):
        if s.get('name') is None:
            print 'Naming %s' % s['filename']
            samples.update({'_id': s['_id']}, {"$set": {'name': s['filename']}}, upsert=False)


def fix_sample_date_added():
    # Update date_added field for samples
    for s in samples.find({'date_added': None}):
        print 'Setting add date', s
        samples.update({'_id': s['_id']}, {"$set": {'date_added': datetime.now()}}, upsert=False)


# Set image quality measures
def set_image_measures(sample_id, image_measures):
    samples.update({'_id': sample_id}, {"$set": image_measures}, upsert=False)


# Human annotations #
#####################
human_annotations = epidermal_db['human_annotations']
# 'sample_id' (id): Link into samples collection
# 'user_id' (id): Annotating user
# 'positions' (array[n] of array[2]): [x,y] positions of detected stomata [px]
# 'margin': Stomata annotation margin [px]


def get_human_annotations(sample_id):
    def resolve(annotation):
        user = get_user_by_id(annotation['user_id'])
        if user is not None:
            annotation['user_name'] = user['email']
        return annotation
    return [resolve(s) for s in human_annotations.find({'sample_id': sample_id})]


def set_human_annotation(sample_id, user_id, positions, margin, base_annotations=None):
    annotation_lookup = {'sample_id': sample_id}
    annotation_record = {'sample_id': sample_id, 'user_id': user_id, 'positions': positions, 'margin': margin,
                         'base_annotations': base_annotations}
    human_annotations.update(annotation_lookup, annotation_record, upsert=True)
    samples.update({'_id': sample_id}, {"$set": {'annotated': True}}, upsert=False)
    samples.update({'_id': sample_id}, {"$set": {'human_position_count': len(positions)}}, upsert=False)
    sample = samples.find_one({'_id': sample_id})
    if sample is not None:
        dataset_id = sample['dataset_id']
        if dataset_id is not None:
            update_dataset_human_annotations(dataset_id)


def get_human_annotation_count():
    return human_annotations.count()


# Fix count where it's missing
def count_human_annotations():
    for s in samples.find({'annotated': True}):
        if s.get('human_position_count') is None:
            human = get_human_annotations(s['_id'])
            n = len(human[0]['positions'])
            s['human_position_count'] = n
            sample_id = s['_id']
            print 'Human counted %02d on %s.' % (n, sample_id)
            samples.update({'_id': sample_id}, {"$set": {'human_position_count': n}}, upsert=False)


# Machine annotations #
#######################
machine_annotations = epidermal_db['machine_annotations']
# 'sample_id' (id): Link into samples collection
# 'model_id' (id): Annotating model
# 'heatmap_filename' (str): Filename of heatmap (numpy)
# 'heatmap_image_filename' (str): Filename of heatmap image data
# 'positions' (array[n] of array[2]): [x,y] positions of detected stomata [px]
# 'margin': Stomata detection margin [px]


def get_machine_annotations(sample_id):
    return [s for s in machine_annotations.find({'sample_id': sample_id})]


def add_machine_annotation(sample_id, model_id, heatmap_filename, heatmap_image_filename, positions, margin):
    annotation_record = {'sample_id': sample_id, 'model_id': model_id, 'heatmap_filename': heatmap_filename,
                         'heatmap_image_filename': heatmap_image_filename, 'positions': positions, 'margin': margin}
    annotation_record['_id'] = machine_annotations.insert_one(annotation_record).inserted_id
    samples.update({'_id': sample_id}, {"$set": {'processed': True}}, upsert=False)
    samples.update({'_id': sample_id}, {"$set": {'machine_position_count': len(positions)}}, upsert=False)
    machine_hopkins = hopkins(np.array(positions))
    samples.update({'_id': sample_id}, {"$set": {'machine_hopkins': machine_hopkins}}, upsert=False)
    return annotation_record


def update_machine_annotation_positions(sample_id, machine_annotation_id, positions):
    machine_annotations.update({'_id': machine_annotation_id}, {"$set": {'positions': positions}}, upsert=False)
    samples.update({'_id': sample_id}, {"$set": {'machine_position_count': len(positions)}}, upsert=False)


def delete_all_machine_annotations():
    r = machine_annotations.delete_many({})
    samples.update_many({}, {"$set": {'processed': False}}, upsert=False)
    print 'Deleted %d machine annotations.' % r.deleted_count
    return r.deleted_count > 0


# Fix count where it's missing
def count_machine_annotations():
    for s in samples.find({'processed': True}):
        if not s.get('machine_position_count'):
            machine = get_machine_annotations(s['_id'])
            n = len(machine[0]['positions'])
            s['machine_position_count'] = n
            sample_id = s['_id']
            print 'Machine counted %02d on %s.' % (n, sample_id)
            samples.update({'_id': sample_id}, {"$set": {'machine_position_count': n}}, upsert=False)


# Fix stats where it's missing
def stat_machine_annotations():
    for s in samples.find({'processed': True}):
        if not s.get('machine_hopkins'):
            machine = get_machine_annotations(s['_id'])
            machine_hopkins = hopkins(np.array(machine[0]['positions']))
            sample_id = s['_id']
            print 'Machine hopkins %.3f  for %s' % (machine_hopkins, str(sample_id))
            samples.update({'_id': sample_id}, {"$set": {'machine_hopkins': machine_hopkins}}, upsert=False)


# Users #
#########
user = epidermal_db['user']
# 'email' (str): User email

def get_user_by_id(user_id):
    return user.find_one({'_id': user_id})


# Models #
##########
models = epidermal_db['models']
# 'name' (str): Model name
# 'margin' (int): Margin at each side that the model does not predict [px]


def get_or_add_model(model_name, margin):
    model = models.find_one({'name': model_name})
    if model is None:
        model = add_model(model_name, margin)
    return model


def add_model(model_name, margin):
    model_record = {'name': model_name, 'margin': margin}
    model_record['_id'] = models.insert_one(model_record).inserted_id
    return model_record


def get_model_by_id(model_id):
    return models.find_one({'_id': model_id})


# Status #
###########
status = epidermal_db['status']
# 'component' (str): Component name for status string
# 'staus' (str): Status string


def get_status(component):
    rec = status.find_one({'component': component})
    if rec is None:
        return 'Unknown'
    return rec['status']


def set_status(component, status_string):
    status.update({'component': component}, {"$set": {'component': component, 'status': status_string}}, upsert=True)


# Helpers
def print_annotation_table():
    for s in samples.find({}):
        if (s.get('human_position_count') is not None) or (s.get('machine_position_count') is not None):
            print 'Hu: %s    Ma: %s   %s' % (s.get('human_position_count'), s.get('machine_position_count'),
                                             s.get('filename'))


# Test
if __name__ == '__main__':
    stat_machine_annotations()
    #delete_all_machine_annotations()
    #for dataset in get_datasets():
    #    if dataset.get('user'):
    #        print dataset['name'], dataset['user']['email']
    # count_human_annotations()
    # count_machine_annotations()
    # stat_machine_annotations()
    # fix_dataset_date_added()
    # fix_sample_date_added()
    # fix_dataset_human_annotation_count()
    # for d in datasets.find({}):
    #     print d
    # fix_dataset_tags()
    # print_annotation_table()
    # fix_default_sample_names()
    # test_db = get_dataset_by_name('Test')
    # unassigned_samples = samples.find({'dataset_id': None})
    # for s in unassigned_samples:
    #     print 'Updating %s...' % (s['filename'])
    #     samples.update({'_id': s['_id']}, {"$set": {'dataset_id': test_db['_id']}}, upsert=False)
    # all_datasets = datasets.find()
    # for d in all_datasets:
    #     if not 'deleted' in d:
    #         print 'Marked dataset %s as not deleted.' % d['name']
    #         datasets.update({'_id': d['_id']}, {"$set": {'deleted': False}}, upsert=False)
