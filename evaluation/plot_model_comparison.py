#!/usr/bvin/env python
# Load model comparison file and generate plot

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re


def get_model_perf(manual_count, model_count):
    #err = np.median(np.abs(np.log(np.divide(manual_count + 0.001, model_count + 0.001))))
    err = np.mean(np.abs(model_count - manual_count))
    return err


def sortmodels(m):
    model_name = m[0]
    nums = re.findall(r'\d+', model_name)
    if nums:
        return int(nums[0])
    else:
        return model_name



def plot_model_perfs(dataset, model_perfs, sample_count):
    models, perfs = zip(*sorted(model_perfs.iteritems(), key=sortmodels))
    n = len(models)
    plt.figure()
    plt.barh(xrange(n), perfs)
    plt.title('Median count errors for dataset %s (%d)' % (dataset, sample_count))
    plt.xlabel('median log(manual count / model count)')
    plt.ylabel('Model')
    plt.yticks(xrange(n), models)
    plt.tight_layout()


def plot_comparison(data):
    data = data.dropna()
    print data
    datasets = np.unique(data['Dataset'])
    print datasets
    models = data.columns[3:]
    print models
    for dataset in datasets:
        dsdata = data[data['Dataset'] == dataset]
        if dsdata.shape[0] < 20:
            continue
        manual_count = dsdata['Manual_count']
        model_perfs = {model: get_model_perf(np.array(manual_count), np.array(dsdata[model])) for model in models}
        plot_model_perfs(dataset, model_perfs, dsdata.shape[0])
    pass


def load_data(filename):
    return pd.DataFrame(pd.read_csv(filename, header=0))


if __name__ == '__main__':
    plot_comparison(load_data('/home/sven2/Downloads/export_model_comparison'))
    plt.show()