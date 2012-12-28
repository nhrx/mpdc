# coding: utf-8
import ast
from collections import OrderedDict

from mpdc.initialize import mpd
from mpdc.libs.utils import is_cached, read_cache, write_cache, \
                            repr_tags, info, warning


class CollectionsManager:

    def __init__(self, collections_filepath):
        self.filepath = collections_filepath
        self.collections = []
        self.need_update = False

    def feed(self, force=False):
        if is_cached('collections') and not force:
            self.collections = read_cache('collections')
        else:
            self.collections = raw_to_optimized(self.read())

    def read(self):
        with open(self.filepath, 'r') as f:
            return f.readlines()

    def add_songs(self, alias, songs_files):
        if (not alias in self.collections or
            not 'mpd_playlist' in self.collections[alias]):
            for song in songs_files[:]:
                if not all(mpd.get_tags(song)):
                    warning('File not added, missing tag(s): [%s]' % song)
                    songs_files.remove(song)
        if alias in self.collections:
            if 'songs' in self.collections[alias]:
                self.collections[alias]['songs'].extend(songs_files)
            else:
                self.collections[alias]['songs'] = songs_files
            if 'mpd_playlist' in self.collections[alias]:
                mpd.add_songs_stored_playlist(alias, songs_files)
        else:
            info('Collection [%s] will be created' % alias)
            self.collections[alias] = {}
            self.collections[alias]['songs'] = songs_files
        self.need_update = True

    def remove_songs(self, alias, songs_files):
        if alias in self.collections and 'songs' in self.collections[alias]:
            remaining_songs = [s for s in self.collections[alias]['songs']
                               if s not in songs_files]
            if 'mpd_playlist' in self.collections[alias]:
                mpd.clear_stored_playlist(alias)
                mpd.add_songs_stored_playlist(alias, remaining_songs)
            self.collections[alias]['songs'] = remaining_songs
            self.need_update = True
        else:
            warning('Collection [%s] doesn\'t exist or contains no song to '
                    'remove' % alias)

    def write_file(self):
        with open(self.filepath, 'w') as f:
            f.write(optimized_to_raw(self.collections))

    def update_cache(self):
        write_cache('collections', self.collections)


# Human-readable format -> dictionary of collections including MPD playlists
def raw_to_optimized(collections_raw):
    collections = OrderedDict()
    alias = ''
    for line in collections_raw:
        if line.startswith('--'):
            alias = line[2:].strip()
            collections[alias] = {}
        elif alias:
            if line.startswith('command:'):
                collections[alias]['command'] = line[8:].strip()
            elif line.startswith('songs:'):
                collections[alias]['songs'] = []
            elif line.strip():
                if ('songs' in collections[alias] and
                    (line.startswith('    ') or line.startswith('\t'))):
                    tags = ast.literal_eval('(%s)' % line.strip())
                    artist, album, title, track = tags
                    matched_songs = mpd.find_multiple(artist=artist,
                                                      album=album,
                                                      title=title,
                                                      track=track)
                    if matched_songs:
                        collections[alias]['songs'].append(matched_songs[0])
                    else:
                        warning('In collection [%s], these tags don\'t match '
                                'any song: %s' % (alias, repr_tags(tags)))
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
            warning('MPD playlist [%s] was ignored because a collection with '
                    'the same name already exists' % playlist)
    return collections


# Dictionary of collections -> human-readable format without MPD playlists
def optimized_to_raw(collections_optimized):
    raw = ''
    for alias in collections_optimized:
        if 'mpd_playlist' in collections_optimized[alias]:
            continue
        raw += '--%s' % alias
        if 'expression' in collections_optimized[alias]:
            raw += '\n' + collections_optimized[alias]['expression'].rstrip()
        if 'command' in collections_optimized[alias]:
            raw += '\ncommand: ' + collections_optimized[alias]['command']
        if ('songs' in collections_optimized[alias] and
           collections_optimized[alias]['songs']):
            raw += '\nsongs:'
            for song in collections_optimized[alias]['songs']:
                song_tags = mpd.get_tags(song)
                raw += '\n    ' + repr_tags(song_tags)
        raw += '\n\n\n'
    return raw.strip()
