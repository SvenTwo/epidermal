#!/usr/bin/env python
# Annotate family and species

import os
from collections import defaultdict
import seaborn as sns
import matplotlib.pyplot as plt

from epidermal import db
from epidermal.config import config


def savefig(name):
    pth = os.path.join(config.get_plot_path(), name + '.pdf')
    plt.gcf().savefig(pth, bbox_inches='tight')


def load_sample_measures():
    sample2measures = {}
    for sample in db.get_samples():
        hopkins = sample.get('machine_hopkins')
        count = sample.get('machine_position_count')
        if hopkins is not None:
            name, _ext = os.path.splitext(sample['name'])
            sample2measures[name] = hopkins, count
    return sample2measures


def annotate_families(filename):
    sample2measures = load_sample_measures()
    family2measures = defaultdict(list)
    with open(filename, 'rt') as fid:
        header = fid.next().split(',')
        for row in fid:
            row = row.strip()
            if row:
                row_data = row.split(',')
                row_fields = {f: v for f, v in zip(header, row_data)}
                measures = sample2measures.get(row_fields['image_id'])
                if measures is not None:
                    hopkins, count = measures
                    family2measures[row_fields['family']].append([hopkins, count])
    for family, measures in family2measures.iteritems():
        if len(measures) > 50:
            measures_x, measures_y = zip(*measures)
            plt.plot(measures_x, measures_y, '.', label=family)
    plt.xlabel('Clusterednes (Hopkins)')
    plt.ylabel('Stomata count')
    plt.legend()
    savefig('measures_by_family')


if __name__ == '__main__':
    annotate_families('/data/Documents/stomata_families.csv')
    plt.show()