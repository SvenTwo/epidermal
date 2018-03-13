#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
# import seaborn as sns
import itertools
import os

from epidermal import db
from epidermal.config import config

# Models-to-ID
model_to_id = {m['name']: m['_id'] for m in db.get_models(details=False, status=db.model_status_trained)}

# Models-to-friendly names
model_to_friendly_name = {
    'main': 'Combined',
    'ginkgo': 'Ginkgo',
    'vt': 'VT',
    'ih': 'IH',
    'test': 'Test',
}


def savefig(name):
    pth = os.path.join(config.plot_path, name + '.pdf')
    plt.gcf().savefig(pth, bbox_inches='tight')


def get_performance(model, testset, bootstrap_count=0):
    r = db.get_validation_results(train_model_id=model_to_id[model], validation_model_id=model_to_id[testset],
                                  image_subset='train')
    cm = r['confusion_matrix']
    p = (cm[0][0] + cm[1][1])
    n = (cm[0][0] + cm[1][1] + cm[1][0] + cm[0][1])
    accuracy = (100.0 * p / n)
    sample = [1] * p + [0] * (n - p)
    if bootstrap_count:
        accs = []
        for _ in xrange(bootstrap_count):
            c = np.random.choice(sample, size=n, replace=True)
            p2 = sum(c)
            accs.append(100.0 * p2 / n)

        lower = max(0.0, np.percentile(accs, 2.5))
        upper = min(1.0, np.percentile(accs, 97.5))
        return accuracy, lower, upper
    else:
        return accuracy


def plot_training_size():
    testsets = ('main', 'test')
    training_sizes = (10, 20, 30, 40, 50, 100, 200, 1000, 'all')
    models = ['%04d_samples' % s for s in training_sizes[:-1]] + ['main']
    x = range(len(models))
    plt.figure()
    for testset in testsets:
        performances = np.asarray([get_performance(m, testset) for m in models])
        plt.plot(x, performances, label=model_to_friendly_name[testset])
        print testset, model_to_id[testset], performances
    plt.xticks(x, training_sizes, rotation=45)
    plt.xlabel('Traning image count')
    plt.ylabel('Accuracy (%)')
    plt.legend()
    savefig('training_size')


def plot_transfer_matrix():
    train_models = ('main', 'ginkgo', 'vt', 'ih')
    test_models = ('main', 'ginkgo', 'vt', 'ih', 'test')
    n_train = len(train_models)
    n_test = len(test_models)
    tm = np.zeros((n_train, n_test))
    for i, train_model in enumerate(train_models):
        for j, test_model in enumerate(test_models):
            tm[i, j] = get_performance(train_model, test_model)

    plt.figure()
    plt.imshow(tm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Training Transfer Accuracies (%)')
    plt.colorbar()
    plt.xticks(np.arange(len(test_models)), [model_to_friendly_name[m] for m in test_models], rotation=45)
    plt.yticks(np.arange(len(train_models)), [model_to_friendly_name[m] for m in train_models], rotation=45)

    thresh = (tm.max() + tm.min()) / 2.
    for i, j in itertools.product(range(n_train), range(n_test)):
        plt.text(j, i, '%.1f' % tm[i, j], horizontalalignment="center",
                 color="white" if tm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('Training dataset')
    plt.xlabel('Testing dataset')
    savefig('transfer_matrix')



if __name__ == '__main__':
    plot_training_size()
    plot_transfer_matrix()
    plt.show()
