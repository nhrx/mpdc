# coding: utf-8
import os
import pickle
from subprocess import check_output, CalledProcessError


# --------------------------------
# Caching functions
# --------------------------------

def cache_last_modified(name):
    filepath = os.path.join(os.path.expanduser('~/.cache'), name + '.mpdc')
    return os.path.getmtime(filepath)


def is_cached(name):
    filepath = os.path.join(os.path.expanduser('~/.cache'), name + '.mpdc')
    return os.path.isfile(filepath)


def read_cache(name):
    filepath = os.path.join(os.path.expanduser('~/.cache'), name + '.mpdc')
    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except IOError:
        warning('Can\'t read cache from: ' + filepath)


def write_cache(name, data):
    filepath = os.path.join(os.path.expanduser('~/.cache'), name + '.mpdc')
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    except IOError:
        warning('Can\'t write cache in: ' + filepath)


# --------------------------------
# Some other functions
# --------------------------------

def esc_quotes(s):
    return s.replace('"', '\\"')


def repr_tags(tags):
    return ', '.join(['"%s"' % esc_quotes(tag) for tag in tags])


def format_mpc_output(raw):
    return [line for line in raw.split('\n') if line != '']


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


def input_box(title, message):
    try:
        data = check_output(['zenity', '--title=' + title, '--entry',
                             '--text=' + message, '--width', '500'])
    except CalledProcessError:
        return None
    else:
        return data.decode().strip()
