# coding: utf-8
import os
import sys
from configparser import ConfigParser

from mpdc.libs.utils import Cache, warning, available_colors


config = ConfigParser()

if not config.read(os.path.expanduser('~/.mpdc')):
    warning('Can\'t read the configuration file, please run mpdc-configure')
    sys.exit(0)

try:
    config['profiles']
    config['profiles']['host[1]']
    config['profiles']['port[1]']
    config['profiles']['password[1]']
    config['mpdc']['collections']
except KeyError:
    warning('Invalid configuration file')
    sys.exit(0)

profiles = {}
for key in config['profiles']:
    if key == 'default':
        continue
    num = int(''.join(filter(str.isdigit, key)))
    if num not in profiles:
        profiles[num] = {
            'host': config['profiles']['host[%d]' % num],
            'port': config['profiles']['port[%d]' % num],
            'password': config['profiles']['password[%d]' % num],
        }
profile = int(config['profiles'].get('default', 1))

colors = ['none']
if 'colors' in config['mpdc']:
    user_colors = [s.strip() for s in config['mpdc']['colors'].split(',')]
    if all(color in available_colors for color in user_colors):
        colors = user_colors

columns = ['artist', 'title', 'album']
available_columns = ['artist', 'album', 'title', 'track', 'genre', 'date',
                     'time', 'filename']
if 'columns' in config['mpdc']:
    user_columns = [s.strip() for s in config['mpdc']['columns'].split(',')]
    if (all(column in available_columns for column in user_columns)):
        columns = user_columns

enable_command = config['mpdc'].get('enable_command', 'n') == 'y'
enable_pager = config['mpdc'].get('enable_pager', 'n') == 'y'
pager = config['mpdc'].get('pager', 'less -R')


# --------------------------------
# Cache initialization
# --------------------------------

cache = Cache(profile)


# --------------------------------
# MPD initialization
# --------------------------------

from mpdc.libs.mpdhelper import MPDHelper
mpd = MPDHelper(profiles[profile]['host'],
                profiles[profile]['password'],
                profiles[profile]['port'])

if not mpd.connect():
    warning('Unable to connect to the MPD server')
    sys.exit(0)

if (not cache.exists('songs_tags') or
    cache.last_modified('songs_tags') < int(mpd.stats()['db_update'])):
    mpd.update_cache()


# --------------------------------
# Collections initialization
# --------------------------------

try:
    open(config['mpdc']['collections'], 'r')
except IOError:
    warning('The collections file [%s] doesn\'t seem readable' %
            config['mpdc']['collections'])
    sys.exit(0)

from mpdc.libs.collectionsmanager import CollectionsManager
collectionsmanager = CollectionsManager(config['mpdc']['collections'])

update_collections = False

if (not cache.exists('playlists') or cache.read('playlists') !=
    mpd.get_stored_playlists_info()):
    cache.write('playlists', mpd.get_stored_playlists_info())
    update_collections = True

if (update_collections or not cache.exists('collections')
    or cache.last_modified('collections') <
    os.path.getmtime(config['mpdc']['collections'])):
    collectionsmanager.feed(force=True)
    collectionsmanager.update_cache()
else:
    collectionsmanager.feed()

collections = collectionsmanager.collections


# --------------------------------
# Lastfm initialization
# --------------------------------

from mpdc.libs.lastfmhelper import LastfmHelper
lastfm = LastfmHelper()

if 'min_similarity' in config['mpdc']:
    LastfmHelper.min_similarity = int(config['mpdc']['min_similarity']) / 100
