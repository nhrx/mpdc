# coding: utf-8
import os
import math
import curses
import pickle
import subprocess
import collections


# --------------------------------
# Cache manager
# --------------------------------

class Cache:
    cache_path = os.path.expanduser('~/.cache/mpdc/{profile}/{name}.mpdc')

    def __init__(self, profile):
        self.p = Cache.cache_path.format(profile=profile, name='{name}')

    def exists(self, name):
        return os.path.isfile(self.p.format(name=name))

    def last_modified(self, name):
        return os.path.getmtime(self.p.format(name=name))

    def read(self, name):
        try:
            with open(self.p.format(name=name), 'rb') as f:
                return pickle.load(f)
        except IOError:
            warning('Cannot read cache from: ' + self.p.format(name=name))

    def write(self, name, data):
        try:
            if not os.path.exists(os.path.dirname(self.p)):
                os.makedirs(os.path.dirname(self.p))
            with open(self.p.format(name=name), 'wb') as f:
                pickle.dump(data, f)
        except IOError:
            warning('Cannot write cache in: ' + self.p.format(name=name))


# --------------------------------
# Colors functions
# --------------------------------

colors_c = {'grey': 30, 'red': 31, 'green': 32, 'yellow': 33,
                    'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37}


def colorize(s, color, bold=False):
    if os.getenv('ANSI_COLORS_DISABLED') is None and color != 'none':
        if bold:
            return '\033[1m\033[{}m{}\033[0m'.format(colors_c[color], s)
        return '\033[{}m{}\033[0m'.format(colors_c[color], s)
    return s


def warning(s):
    print(colorize('[warning] ', 'yellow', bold=True) + s)


def info(s):
    print(colorize('[info] ', 'green', bold=True) + s)


# --------------------------------
# Columns width
# --------------------------------

columns_w = {
    'artist': 1,
    'album': 1.5,
    'title': 1.5,
    'date': 0.25,
    'time': 0.25,
    'track': 0.25,
    'genre': 0.5,
    'filename': 2
}


def columns_width(columns):
    curses.setupterm()
    term_w = curses.tigetnum('cols')
    t_w = sum(columns_w[column] for column in columns)
    c_w = {column: int(term_w * columns_w[column] / t_w) for column in columns}
    return c_w, term_w


# --------------------------------
# Cosine similarity
# --------------------------------

def similarity(a, b):
    scalar = sum(a[k] * b[k] for k in a if k in b)
    norm_a = math.sqrt(sum(v ** 2 for v in a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in b.values()))
    return scalar / (norm_a * norm_b)


# --------------------------------
# Some other functions
# --------------------------------

def esc_quotes(s):
    return s.replace('"', '\\"')


def repr_tags(tags):
    return ', '.join(['"' + esc_quotes(tag) + '"' for tag in tags])


def format_mpc_output(raw):
    return [line for line in raw.split('\n') if line]


def input_box(title, message):
    try:
        data = subprocess.check_output(['zenity', '--title=' + title,
                                        '--entry', '--text=' + message,
                                        '--width', '500'])
    except subprocess.CalledProcessError:
        return None
    return data.decode().strip()


# --------------------------------
# Sorted set
# From http://code.activestate.com/recipes/576694/
# --------------------------------

class OrderedSet(collections.MutableSet):
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
