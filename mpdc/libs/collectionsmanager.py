# coding: utf-8
import ast
from collections import OrderedDict

from mpdc.initialize import mpd, cache
from mpdc.libs.utils import repr_tags, info, warning


class CollectionsManager:

    def __init__(self, collections_filepath):
        self.path = collections_filepath
        self.collections = []
        self.need_update = False

    @property
    def c(self):
        return self.collections

    def feed(self, force=False):
        if cache.exists('collections') and not force:
            self.collections = cache.read('collections')
        else:
            with open(self.path, 'r') as f:
                self.collections = raw_to_optimized(f.readlines())

    def add_songs(self, alias, songs_files):
        if not alias in self.c or not 'mpd_playlist' in self.c[alias]:
            for song in songs_files[:]:
                if not all(mpd.get_tags(song)):
                    warning('[{}] was not added (missing tags)'.format(song))
                    songs_files.remove(song)
        if alias in self.c:
            if 'songs' in self.c[alias]:
                self.collections[alias]['songs'].extend(songs_files)
            else:
                self.collections[alias]['songs'] = songs_files
            if 'mpd_playlist' in self.c[alias]:
                mpd.add_songs_stored_playlist(alias, songs_files)
        else:
            info('Collection [{}] will be created'.format(alias))
            self.collections[alias] = {}
            self.collections[alias]['songs'] = songs_files
        self.need_update = True

    def remove_songs(self, alias, songs_files):
        if alias in self.c and 'songs' in self.c[alias]:
            remaining_songs = [s for s in self.c[alias]['songs']
                               if s not in songs_files]
            if 'mpd_playlist' in self.c[alias]:
                mpd.clear_stored_playlist(alias)
                mpd.add_songs_stored_playlist(alias, remaining_songs)
            self.collections[alias]['songs'] = remaining_songs
            self.need_update = True
        else:
            warning('Collection [{}] does not exist or contains no song to '
                    'remove'.format(alias))

    def write_file(self):
        with open(self.path, 'w') as f:
            f.write(optimized_to_raw(self.collections))

    def update_cache(self):
        cache.write('collections', self.collections)


# Human-readable format -> dictionary of collections including MPD playlists
def raw_to_optimized(collections_raw):
    collections = OrderedDict()
    alias = ''
    for line in collections_raw:
        if line.startswith('--'):
            alias = (line[2:] if line[2] not in '@#' else line[3:]).strip()
            collections[alias] = {}
            if line[2] == '@':
                collections[alias]['sort'] = True
            elif line[2] == '#':
                collections[alias]['special'] = True
        elif alias:
            if line.startswith('command:'):
                collections[alias]['command'] = line[8:].strip()
            elif line.startswith('songs:'):
                collections[alias]['songs'] = []
            elif line.strip():
                if ('songs' in collections[alias] and
                   (line.startswith('    ') or line.startswith('\t'))):
                    tags = ast.literal_eval('({})'.format(line.strip()))
                    artist, album, title, track = tags
                    matched_songs = mpd.find_multiple(artist=artist,
                                                      album=album,
                                                      title=title,
                                                      track=track)
                    if matched_songs:
                        collections[alias]['songs'].append(matched_songs[0])
                    else:
                        warning('In collection [{}], these tags do not match '
                                'any song: {}'.format(alias, repr_tags(tags)))
                else:
                    if 'expression' not in collections[alias]:
                        collections[alias]['expression'] = line
                    else:
                        collections[alias]['expression'] += line
    # add MPD native playlists
    for playlist in mpd.get_stored_playlists():
        if playlist not in collections:
            collections[playlist] = {'mpd_playlist': True,
                                     'songs':
                                       mpd.get_stored_playlist_songs(playlist)}
        else:
            warning('MPD playlist [{}] was ignored because a collection with '
                    'the same name already exists'.format(playlist))
    return collections


# Dictionary of collections -> human-readable format without MPD playlists
def optimized_to_raw(collections_optimized):
    raw = ''
    for alias, collection in collections_optimized.items():
        if 'mpd_playlist' in collection:
            continue
        elif 'sort' in collection:
            raw += '--@' + alias
        elif 'special' in collection:
            raw += '--#' + alias
        else:
            raw += '--' + alias
        if 'expression' in collection:
            raw += '\n' + collection['expression'].rstrip()
        if 'command' in collection:
            raw += '\ncommand: ' + collection['command']
        if 'songs' in collection and collection['songs']:
            raw += '\nsongs:'
            for song in collection['songs']:
                raw += '\n    ' + repr_tags(mpd.get_tags(song))
        raw += '\n\n\n'
    return raw.strip()
