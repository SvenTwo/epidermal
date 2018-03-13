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


def get_datasets_by_tag(tag_name):
    return datasets.find({'tags': {'$in': [tag_name]}, 'deleted': False})


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
# 'date_added': datetime when the sample was uploaded


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
        for dataset in get_datasets_by_tag(train_label):
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
    if dataset_id is not None:
        query = {'dataset_id': dataset_id}
        return sorted(list(samples.find(query)), key=lambda x: x['name'])
    else:
        return samples.find({})


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


# Sample queue for non-primary models and image validation runs #
#################################################################
sample_queue = epidermal_db['sample_queue']
# 'sample_id' (id): Link into samples collection
# 'model_id' (id): Link into model collection
# 'validation_model_id' (id): Link into model collection for validation set queue items


def get_queued_samples(model_id=None):
    query = {}
    if model_id is not None:
        query['model_id'] = model_id
    return sample_queue.find(query)


def queue_sample(sample_id, model_id):
    rec = {'sample_id': sample_id, 'model_id': model_id}
    sample_queue.update(rec, rec, upsert=True)


def queue_validation(train_model_id, validation_model_id):
    rec = {'validation_model_id': validation_model_id, 'model_id': train_model_id}
    sample_queue.update(rec, rec, upsert=True)


def unqueue_sample(queue_item_id):
    sample_queue.delete_one({'_id': queue_item_id})



# Image validation runs #
#########################
validation_results = epidermal_db['validation_results']
# 'train_model_id' (id): Evaluated model
# 'validation_model_id' (id): Model to which the evaluation dataset belongs
# 'image_subset' (str): Which dataset (train, val, test)
# 'confusion_matrix' (list(2) of list(2)): Count of [true_label][prediction] with 0=distractor, 1=target
# 'worst_predictions' (dict('Distractor', 'Target') of list of [sample_name, prediction_value]): Top 25 worst
#                                                                                               (mis-)classifications

def save_validation_results(train_model_id, validation_model_id, image_subset, confusion_matrix, worst_predictions):
    query = {
        'train_model_id': train_model_id,
        'validation_model_id': validation_model_id,
        'image_subset': image_subset
    }
    results = dict(query)
    results['confusion_matrix'] = confusion_matrix
    results['worst_predictions'] = worst_predictions
    validation_results.update(query, results, upsert=True)


def get_all_validation_results(train_model_id=None, validation_model_id=None):
    q = {}
    if train_model_id is not None:
        q['train_model_id'] = train_model_id
    if validation_model_id is not None:
        q['validation_model_id'] = validation_model_id
    return list(validation_results.find(q))


def get_validation_results(train_model_id, validation_model_id, image_subset):
    return validation_results.find_one({'train_model_id': train_model_id, 'validation_model_id': validation_model_id,
                                        'image_subset': image_subset})


def get_validation_results_by_id(val_id):
    return validation_results.find_one({'_id': val_id})



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


def get_machine_annotations(sample_id, model_id=None):
    if model_id is None:
        model_id = get_primary_model()['_id']
    return list(machine_annotations.find({'sample_id': sample_id, 'model_id': model_id}))


def get_all_model_machine_annotations(sample_id):
    return list(machine_annotations.find({'sample_id': sample_id}))


def get_machine_annotations_for_model(model_id):
    return machine_annotations.find({'model_id': model_id})


def remove_machine_annotations_for_model(model_id):
    return machine_annotations.delete_many({'model_id': model_id})


def add_machine_annotation(sample_id, model_id, heatmap_filename, heatmap_image_filename, positions, margin,
                           is_primary_model):
    annotation_query = {'sample_id': sample_id, 'model_id': model_id}
    annotation_record = {'sample_id': sample_id, 'model_id': model_id, 'heatmap_filename': heatmap_filename,
                         'heatmap_image_filename': heatmap_image_filename, 'positions': positions, 'margin': margin}
    machine_annotations.update(annotation_query, annotation_record, upsert=True)
    annotation_record['_id'] = machine_annotations.find_one(annotation_query)['_id']
    if is_primary_model:
        set_primary_machine_annotation(sample_id, positions)
    return annotation_record


def set_primary_machine_annotation(sample_id, positions):
    if positions is None:
        sample_update = {'processed': False,
                         'machine_position_count': None,
                         'machine_hopkins': None}
    else:
        sample_update = {'processed': True,
                         'machine_position_count': len(positions),
                         'machine_hopkins': hopkins(np.array(positions))}
    samples.update({'_id': sample_id}, {"$set": sample_update}, upsert=False)


def update_machine_annotation_positions(sample_id, machine_annotation_id, positions, is_primary_model):
    print 'update_machine_annotation_positions'
    print 'sample_id', sample_id
    print 'machine_annotation_id', machine_annotation_id
    print 'positions', positions
    print 'is_primary_model', is_primary_model
    machine_annotations.update({'_id': machine_annotation_id}, {"$set": {'positions': positions}}, upsert=False)
    if is_primary_model:
        samples.update({'_id': sample_id}, {"$set": {'machine_position_count': len(positions)}}, upsert=False)


def delete_all_machine_annotations():
    r = machine_annotations.delete_many({})
    sample_update = {'processed': False,
                     'machine_position_count': None,
                     'machine_hopkins': None}
    samples.update_many({}, {"$set": sample_update}, upsert=False)
    print 'Deleted %d machine annotations.' % r.deleted_count
    return r.deleted_count > 0


# Update the machine position count and hopkins field based on primary model results
def fix_primary_machine_annotations():
    model_id = get_primary_model()['_id']
    for s in samples.find():
        machine = get_machine_annotations(s['_id'], model_id=model_id)
        if not machine:
            set_primary_machine_annotation(s['_id'], None)
        else:
            set_primary_machine_annotation(s['_id'], machine[0]['positions'])


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
# 'date_added' (datetime): When the model training was issued
# 'status' (str): 'scheduled', 'training' or 'trained'
model_status_scheduled = 'scheduled'
model_status_training = 'training'
model_status_trained = 'trained'
model_status_failed = 'failed'


def get_or_add_model(model_name, margin):
    model = models.find_one({'name': model_name})
    if model is None:
        model = add_model(model_name, margin)
    return model


def get_models(details=False, status=None):
    filter = {}
    if status is not None:
        filter['status'] = status
    rval = list(models.find(filter))
    if details:
        for model in rval:
            if 'date_added' in model:
                model['date_added'] = model['date_added'].strftime('%Y-%m-%d %H:%M')
            else:
                model['date_added'] = 'unknown'
            if not 'primary' in model:
                model['primary'] = False
            model['machine_annotation_count'] = machine_annotations.count({'model_id': model['_id']})
    return rval


def add_model(model_name, margin, sample_limit=None, train_tag='train', scheduled_primary=False,
              status=model_status_scheduled):
    model_record = {'name': model_name,
                    'margin': margin,
                    'primary': False,
                    'status': status,
                    'sample_limit': sample_limit,
                    'train_tag': train_tag,
                    'scheduled_primary': scheduled_primary}
    model_record['_id'] = models.insert_one(model_record).inserted_id
    return model_record


def delete_model(model_id):
    if model_id is None:
        raise RuntimeError('Invalid model.')
    models.delete_one({'_id': model_id})


def set_model_parameters(model_id, new_settings):
    result = models.update_one({'_id': model_id}, {"$set": new_settings}, upsert=False)
    print 'result', result
    if not result.modified_count:
        raise RuntimeError('set_model_parameters: Model ID %s not found.' % str(model_id))


def get_model_by_id(model_id):
    return models.find_one({'_id': model_id})


def get_model_by_name(model_name):
    return models.find_one({'name': model_name})


def rename_model(old_model_name, new_model_name):
    if models.find_one({'name': new_model_name}):
        raise RuntimeError('Target name exists.')
    result = models.update_one({'name': old_model_name}, {"$set": {'name': new_model_name}}, upsert=False)
    if not result.modified_count:
        raise RuntimeError('set_primary_model: Model ID %s not found.' % str(model_id))


def get_primary_model():
    return models.find_one({'primary': True})


def set_primary_model(model_id):
    previous_primary = get_primary_model()
    result = models.update_one({'_id': model_id}, {"$set": {'primary': True}}, upsert=False)
    if not result.modified_count:
        raise RuntimeError('set_primary_model: Model ID %s not found.' % str(model_id))
    if previous_primary is not None:
        models.update_one({'_id': previous_primary['_id']}, {"$set": {'primary': False}}, upsert=False)
    fix_primary_machine_annotations()


def set_model_status(model_id, new_status):
    assert new_status in {model_status_scheduled, model_status_training, model_status_trained, model_status_failed}
    models.update_one({'_id': model_id}, {"$set": {'status': new_status}}, upsert=False)



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
    fix_primary_machine_annotations()
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
