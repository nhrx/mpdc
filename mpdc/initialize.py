# coding: utf-8
import os
import sys
from configparser import ConfigParser

from mpdc.libs.utils import is_cached, cache_last_modified, read_cache, \
                            write_cache, warning, available_colors


config = ConfigParser()

if not config.read(os.path.expanduser('~/.mpdc')):
    warning('Can\'t read the configuration file, please run mpdc-configure')
    sys.exit(0)

try:
    config['mpd']['host']
    config['mpd']['password']
    config['mpd']['port']
    config['mpdc']['collections']
except KeyError:
    warning('Invalid configuration file')
    sys.exit(0)

colors = ['none', 'none', 'none']
if 'colors' in config['mpdc']:
    user_colors = [s.strip() for s in config['mpdc']['colors'].split(',')]
    if (len(user_colors) == 3 and
        all(color in available_colors for color in user_colors)):
        colors = user_colors

if config['mpdc'].get('playlists_preserve_order', 'n') == 'y':
    playlists_preserve_order = True
else:
    playlists_preserve_order = False

if config['mpdc'].get('enable_command', 'n') == 'y':
    enable_command = True
else:
    enable_command = False


# --------------------------------
# MPD initialization
# --------------------------------

from mpdc.libs.mpdhelper import MPDHelper
mpd = MPDHelper(config['mpd']['host'], config['mpd']['password'],
                config['mpd']['port'])

if not mpd.connect():
    warning('Unable to connect to the MPD server')
    sys.exit(0)

if (not is_cached('songs_tags') or
    cache_last_modified('songs_tags') < int(mpd.stats()['db_update'])):
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

if (not is_cached('playlists') or read_cache('playlists') !=
    mpd.get_stored_playlists_info()):
    write_cache('playlists', mpd.get_stored_playlists_info())
    update_collections = True

if (update_collections or not is_cached('collections')
    or cache_last_modified('collections') <
    os.path.getmtime(config['mpdc']['collections'])):
    collectionsmanager.feed(force=True)
    collectionsmanager.update_cache()
else:
    collectionsmanager.feed()

collections = collectionsmanager.collections


# --------------------------------
# LastFM initialization
# --------------------------------

from mpdc.libs.lastfmhelper import LastfmHelper
lastfm = LastfmHelper()

if 'min_similarity' in config['mpdc']:
    LastfmHelper.min_similarity = int(config['mpdc']['min_similarity']) / 100
