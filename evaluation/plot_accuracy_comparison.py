#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
# import seaborn as sns
import itertools
import os

from epidermal import db
from epidermal.config import config

# Models-to-ID
all_models = list(db.get_models(details=False, status=db.model_status_trained)) \
             + list(db.get_models(details=False, status=db.model_status_dataset))
model_to_id = {m['name']: m['_id'] for m in all_models}

# Models-to-friendly names
model_to_friendly_name = {
    'all': 'Combined',
    'main': 'Combined',
    'cuticle_train': 'Cuticle',
    'cuticle_test': 'Cuticle',
    'ginkgo': 'Ginkgo',
    'ginkgo_test': 'Ginkgo',
    'populus': 'Populus',
    '200xtrain': '200x',
    '200xtest': '200x',
    '400xtrain': '400x',
    '400xtest': '400x',
    'vt': 'VT',
    'ih': 'IH',
    'test': 'Combined',
}


def savefig(name):
    pth = os.path.join(config.get_plot_path(), name + '.pdf')
    plt.gcf().savefig(pth, bbox_inches='tight')


def get_performance(model, testset, bootstrap_count=0, measure='accuracy'):
    r = db.get_validation_results(train_model_id=model_to_id[model], validation_model_id=model_to_id[testset],
                                  image_subset='train')
    if r is None:
        return 0.0
    cm = r['confusion_matrix']
    tp = cm[1][1]
    fp = cm[0][1]
    fn = cm[1][0]
    tn = cm[0][0]
    p = (tp + tn)
    n = (tp + fp + fn + tn)
    if measure == 'accuracy':
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
    elif measure == 'precision':
        precision = float(tp) / (tp + fp)
        return precision
    elif measure == 'recall':
        recall = float(tp) / (tp + fn)
        return recall


def plot_training_size():
    testsets = ('main', 'test')
    testset_names = ('Train', 'Test')
    training_sizes = (10, 20, 30, 40, 50, 100, 200, 1000, 'all')
    models = ['%04d_samples' % s for s in training_sizes[:-1]] + ['main']
    x = range(len(models))
    plt.figure()
    for name, testset in zip(testset_names, testsets):
        performances = np.asarray([get_performance(m, testset) for m in models])
        plt.plot(x, performances, label=name)
        print testset, model_to_id[testset], performances
    plt.xticks(x, training_sizes, rotation=45)
    plt.xlabel('Traning image count')
    plt.ylabel('Accuracy (%)')
    plt.title('Accuracy by training image count')
    plt.legend()
    savefig('training_size')


def plot_transfer_matrix(measure):
    train_models = ('ginkgo', 'cuticle_train', '400xtrain', '200xtrain', 'main')
    test_models = ('ginkgo_test', 'cuticle_test', '400xtest', '200xtest', 'test')
    n_train = len(train_models)
    n_test = len(test_models)
    tm = np.zeros((n_train, n_test))
    for i, train_model in enumerate(train_models):
        for j, test_model in enumerate(test_models):
            tm[i, j] = get_performance(train_model, test_model, measure=measure)

    measure_format, thresh, vmin, vmax, plbl = {
        'accuracy': ('%.1f', 75.0, 50, 100, 'accuracies'),
        'precision': ('%.2f', 0.75, 0.5, 1, 'precision'),
        'recall': ('%.2f', 0.75, 0.5, 1, 'recall'),
    }[measure]

    plt.figure()
    plt.imshow(tm, interpolation='nearest', cmap=plt.cm.Blues, vmin=vmin, vmax=vmax)
    plt.title('Training transfer %s (%%)' % plbl)
    plt.colorbar()
    plt.xticks(np.arange(len(test_models)), [model_to_friendly_name[m] for m in test_models], rotation=45)
    plt.yticks(np.arange(len(train_models)), [model_to_friendly_name[m] for m in train_models], rotation=45)

    for i, j in itertools.product(range(n_train), range(n_test)):
        plt.text(j, i, measure_format % tm[i, j], horizontalalignment="center",
                 color="white" if tm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('Training dataset')
    plt.xlabel('Testing dataset')
    savefig('transfer_matrix_' + measure)


if __name__ == '__main__':
    plot_training_size()
    plot_transfer_matrix(measure='accuracy')
    plot_transfer_matrix(measure='precision')
    plot_transfer_matrix(measure='recall')
    plt.show()
