#!/usr/bin/env python2.7
# List samples by date

from collections import defaultdict

from epidermal import db


if __name__ == '__main__':
    samples_by_date = defaultdict(int)
    for sample in db.samples.find({}):
        da = sample.get('date_added')
        if da:
            da = da.date()
        samples_by_date[da] += 1
    for k, v in sorted(samples_by_date.iteritems()):
        print k, v
