# coding: utf-8
import os
import pickle
from collections import MutableSet
from subprocess import check_output, CalledProcessError
from math import sqrt


# --------------------------------
# Caching functions
# --------------------------------

cache_dir = os.path.expanduser('~/.cache/mpdc')

def cache_last_modified(name):
    filepath = os.path.join(cache_dir, name + '.mpdc')
    return os.path.getmtime(filepath)


def is_cached(name):
    filepath = os.path.join(cache_dir, name + '.mpdc')
    return os.path.isfile(filepath)


def read_cache(name):
    filepath = os.path.join(cache_dir, name + '.mpdc')
    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except IOError:
        warning('Can\'t read cache from: ' + filepath)


def write_cache(name, data):
    filepath = os.path.join(cache_dir, name + '.mpdc')
    try:
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    except IOError:
        warning('Can\'t write cache in: ' + filepath)


# --------------------------------
# Colors functions
# --------------------------------

available_colors = {'grey': 30, 'red': 31, 'green': 32, 'yellow': 33,
                    'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37}

def colorize(s, color, bold=False):
    if os.getenv('ANSI_COLORS_DISABLED') is None and color != 'none':
        if bold:
            return '\033[1m\033[%dm%s\033[0m' % (available_colors[color], s)
        else:
            return '\033[%dm%s\033[0m' % (available_colors[color], s)
    else:
        return s


def warning(s):
    print(colorize('[warning] ', 'yellow', bold=True) + s)


def info(s):
    print(colorize('[info] ', 'green', bold=True) + s)


# --------------------------------
# Cosine similarity
# --------------------------------

def similarity(a, b):
    scalar = sum(a[k] * b[k] for k in a if k in b)
    norm_a = sqrt(sum(v ** 2 for v in a.values()))
    norm_b = sqrt(sum(v ** 2 for v in b.values()))
    return scalar / (norm_a * norm_b)


# --------------------------------
# Some other functions
# --------------------------------

def esc_quotes(s):
    return s.replace('"', '\\"')


def repr_tags(tags):
    return ', '.join(['"%s"' % esc_quotes(tag) for tag in tags])


def format_mpc_output(raw):
    return [line for line in raw.split('\n') if line != '']


def input_box(title, message):
    try:
        data = check_output(['zenity', '--title=' + title, '--entry',
                             '--text=' + message, '--width', '500'])
    except CalledProcessError:
        return None
    else:
        return data.decode().strip()


# --------------------------------
# Sorted set
# From http://code.activestate.com/recipes/576694/
# --------------------------------

class OrderedSet(MutableSet):
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    issubset = property(lambda self: self.__le__)
    issuperset = property(lambda self: self.__ge__)
