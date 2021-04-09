#!/usr/bin/env python2.7
# Find all datasets without tags and older than the timeout period specified in the configuration, and delete them.

from config import config
import db
from datetime import datetime, timedelta


def delete_datasets(dataset_ids):
    print 'Deleting %d datasets...' % len(dataset_ids)
    for dataset_id in dataset_ids:
        db.delete_dataset(dataset_id=dataset_id,
                          recycle=False,
                          delete_files=True)


def find_old_datasets():
    # Find all datasets without tag older than the threshold duration.
    threshold_date = datetime.now() - timedelta(days=config.automatic_deletion_days)
    old_datasets = db.get_untagged_old_datasets(threshold_date)
    return map(lambda ds: ds['_id'], old_datasets)


if __name__ == '__main__':
    delete_datasets(find_old_datasets())
