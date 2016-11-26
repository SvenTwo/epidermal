#!/usr/bin/env python
# Image sample database. DB is connected on module import

import pymongo
from bson.objectid import ObjectId

client = pymongo.MongoClient()
epidermal_db = client.epidermal



### Samples ###
###############
samples = epidermal_db['samples']
# 'filename' (str): Filename (without path) of image
# 'processed' (bool): Whether it has been processed by at least one model
# 'annotated' (bool): Whether it has been annotated by at least one human
# 'error' (bool): Could not process?
# 'error_string' (str): Error string if there was a problem with the sample
# 'size': array[2]: Image size [px]

def get_unprocessed_samples():
    return [s for s in samples.find({'processed': False, 'error': False})]

def get_processed_samples():
    return [s for s in samples.find({'processed': True, 'error': False})]

def get_error_samples():
    return [s for s in samples.find({'error': True})]

def add_sample(filename):
    sample_record = { 'filename': filename, 'size': None, 'processed': False, 'annotated': False, 'error': False, 'error_string': None }
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
    return (r.deleted_count == 1)


### Human annotations ###
#########################
human_annotations = epidermal_db['human_annotations']
# 'sample_id' (id): Link into samples collection
# 'user_id' (id): Annotating user
# 'positions' (array[n] of array[2]): [x,y] positions of detected stomata [px]
# 'margin': Stomata annotation margin [px]

def get_human_annotations(sample_id):
    return [s for s in human_annotations.find({'sample_id': sample_id})]

def add_human_annotation(sample_id, user_id, positions, margin):
    annotation_record = { 'sample_id': sample_id, 'user_id': user_id, 'positions': positions, 'margin': margin }
    annotation_record['_id'] = human_annotations.insert_one(annotation_record).inserted_id
    samples.update({'_id':sample_id}, {"$set": { 'annotated': True } }, upsert=False)
    return annotation_record


### Machine annotations ###
###########################
machine_annotations = epidermal_db['human_annotations']
# 'sample_id' (id): Link into samples collection
# 'model_id' (id): Annotating model
# 'heatmap_filename' (str): Filename of heatmap (numpy)
# 'heatmap_image_filename' (str): Filename of heatmap image data
# 'positions' (array[n] of array[2]): [x,y] positions of detected stomata [px]
# 'margin': Stomata detection margin [px]

def get_machine_annotations(sample_id):
    return [s for s in machine_annotations.find({'sample_id': sample_id})]

def add_machine_annotation(sample_id, model_id, heatmap_filename, heatmap_image_filename, positions, margin):
    annotation_record = { 'sample_id': sample_id, 'model_id': model_id, 'heatmap_filename': heatmap_filename, 'heatmap_image_filename': heatmap_image_filename, 'positions': positions, 'margin': margin }
    annotation_record['_id'] = machine_annotations.insert_one(annotation_record).inserted_id
    samples.update({'_id':sample_id}, {"$set": { 'processed': True } }, upsert=False)
    return annotation_record



### Users ###
#############
users = epidermal_db['users']
# 'name' (str): Username

def get_default_user():
    user = users.find_one({'name': 'human'})
    if user is None:
        user = add_user('human')
    return user

def add_user(name):
    user_record = { 'name': name }
    user_record['_id'] = users.insert_one(user_record).inserted_id
    return user_record

def get_user_by_id(user_id):
    return users.find_one({'_id': user_id})



### Models ###
#############
models = epidermal_db['models']
# 'name' (str): Model name
# 'margin' (int): Margin at each side that the model does not predict [px]

def get_or_add_model(model_name, margin):
    model = users.find_one({'name': model_name})
    if model is None:
        model = add_model(model_name, margin)
    return model

def add_model(model_name, margin):
    model_record = { 'name': model_name, 'margin': margin }
    model_record['_id'] = models.insert_one(model_record).inserted_id
    return model_record

def get_model_by_id(model_id):
    return models.find_one({'_id': model_id})


### Status ###
###############
status = epidermal_db['status']
# 'component' (str): Component name for status string
# 'staus' (str): Status string
def get_status(component):
    rec = status.find_one({'component': component})
    if rec is None: return 'Unknown'
    return rec['status']

def set_status(component, status_string):
    status.update({'component': component}, {"$set": {'component': component, 'status': status_string}}, upsert=True)