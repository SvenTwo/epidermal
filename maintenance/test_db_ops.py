from epidermal import db
from epidermal.cleanup_old_datasets import find_old_datasets
from bson import ObjectId
from datetime import datetime

if __name__ == '__main__':
    db.datasets.update_one({'_id': ObjectId('5d19863fbca3b773ba9601a4')}, {'$set': {'date_accessed': datetime(year=2019, month=5, day=31)}}, upsert=False)
    for dbid in find_old_datasets():
        print 'del', db.get_dataset_by_id(dbid)['name']
