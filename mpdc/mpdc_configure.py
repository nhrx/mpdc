# coding: utf-8
import os
import argparse
from configparser import ConfigParser

from mpdc.libs.utils import info, warning


def configure(args):
    if args.switch:
        change_default_profile(args.switch)
        return
    config = ConfigParser()
    config.add_section('profiles')
    config['profiles']['host[1]'] = input('>> MPD host [localhost]: ') or \
                                    'localhost'
    config['profiles']['port[1]'] = input('>> MPD port [6600]: ') or '6600'
    config['profiles']['password[1]'] = input('>> MPD password []: ') or ''
    print('\n')

    config.add_section('mpdc')
    print('Later, you will propably need to store and edit your collections/'
          'playlists in a specific file. Please create an empty file '
          '(e.g. collections.mpdc) where you want and write its path below.')

    while True:
        path = input('>> Full path of the collections file: ')
        if os.path.isfile(path):
            break
        warning('Cannot find the file: ' + path)
    print('\n')
    config['mpdc']['collections'] = path

    colors = input('>> Enable colors [Y/n]: ').lower() or 'y'
    if colors == 'y':
        config['mpdc']['colors'] = 'green, red, blue'
    print('\n')

    config['mpdc']['columns'] = 'artist, title, album'

    filepath = os.path.expanduser('~/.mpdc')
    try:
        with open(filepath, 'w') as configfile:
            config.write(configfile)
            info('Writing configuration file in: ' + filepath)
    except IOError:
        warning('Cannot write configuration file in: ' + filepath)


def change_default_profile(profile):
    config = ConfigParser()
    filepath = os.path.expanduser('~/.mpdc')
    if not config.read(filepath):
        warning('Cannot read the configuration file, run mpdc-configure')
        return
    config['profiles']['default'] = str(profile)
    try:
        with open(filepath, 'w') as configfile:
            config.write(configfile)
            info('Writing configuration file in: ' + filepath)
    except IOError:
        warning('Cannot write configuration file in: ' + filepath)


# --------------------------------
# Commands parser
# --------------------------------

def main():
    argparser = argparse.ArgumentParser(add_help=False)
    argparser.set_defaults(func=configure)
    argparser.add_argument('--switch', type=int, action='store')

    args = argparser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
