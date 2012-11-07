# coding: utf-8
import os
from configparser import ConfigParser

from mpdc.libs.utils import info, warning


def main():
    config = ConfigParser()

    config.add_section('mpd')
    config['mpd']['host'] = input('>> MPD host [localhost]: ') or 'localhost'
    config['mpd']['port'] = input('>> MPD port [6600]: ') or '6600'
    config['mpd']['password'] = input('>> MPD password []: ') or ''
    print('\n')

    config.add_section('mpdc')
    print('Later, you will propably need to store and edit your collections/'
          'playlists in a specific file. Please create an empty file '
          '(e.g. collections.mpdc) where you want and write its path below.')

    while True:
        path = input('>> Full path of the collections file: ')
        if not os.path.isfile(path):
            warning('Can\'t find the file: ' + path)
        else:
            break
    print('\n')
    config['mpdc']['collections'] = path

    colors = input('>> Enable colors [Y/n]: ').lower() or 'y'
    if colors == 'y':
        config['mpdc']['colors'] = 'red, green, blue'
    print('\n')

    filepath = os.path.expanduser('~/.mpdc')
    try:
        with open(filepath, 'w') as configfile:
            config.write(configfile)
            info('Writing configuration file in: ' + filepath)
    except IOError:
        warning('Can\'t write configuration file in: ' + filepath)

if __name__ == '__main__':
    main()
