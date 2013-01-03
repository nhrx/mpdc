# coding: utf-8
from itertools import chain
from collections import OrderedDict
from subprocess import check_output, Popen, PIPE, STDOUT

import mpd

from mpdc.libs.utils import is_cached, read_cache, write_cache, \
                            format_mpc_output, OrderedSet


# this class uses mpc or python-mpd2 depending on which provides the best
# performances

class MPDHelper:

    def __init__(self, host, password, port):
        self.host = host
        self.port = str(port)
        self.password = password
        self.mpdclient = mpd.MPDClient()
        if password:
            self.mpc_c = ['mpc', '-h', password + '@' + host, '-p', self.port]
        else:
            self.mpc_c = ['mpc', '-h', host, '-p', self.port]
        self.mpc_c_str = ' '.join(self.mpc_c)

        self.all_songs = None
        self.all_songs_tags = None
        self.all_songs_info = None
        self.first_lately_added_song = None

    def connect(self):
        try:
            check_output(self.mpc_c)
            self.mpdclient.connect(self.host, self.port)
            if self.password:
                self.mpdclient.password(self.password)
        except Exception:
            return False
        else:
            return True

    def stats(self):
        return self.mpdclient.stats()

# Playlist functions

    def add(self, songs_files):
        p = Popen(self.mpc_c + ['add'], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        p.communicate(input=bytes('\n'.join(songs_files), 'utf-8'))
        self.first_lately_added_song = songs_files[0]

    def insert(self, songs_files):
        p = Popen(self.mpc_c + ['insert'], stdin=PIPE, stdout=PIPE,
                  stderr=STDOUT)
        p.communicate(input=bytes('\n'.join(songs_files), 'utf-8'))
        self.first_lately_added_song = songs_files[0]

    def remove(self, songs_files):
        positions = self.get_playlist_positions()
        songs_ids = [positions[s] for s in songs_files if s in positions]
        songs_ids = map(str, list(chain.from_iterable(songs_ids)))
        p = Popen(self.mpc_c + ['del'], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        p.communicate(input=bytes('\n'.join(songs_ids), 'utf-8'))

    def replace(self, songs_files):
        self.clear()
        self.add(songs_files)

    def play(self, song_position=1):
        self.mpdclient.play(song_position - 1)

    def play_file(self, song_file):
        positions = self.get_playlist_positions()
        if song_file in positions:
            self.play(positions[song_file][0])

    def clear(self):
        self.mpdclient.clear()

    def crop(self):
        check_output(self.mpc_c + ['crop'])

    def get_playlist_songs(self):
        output = check_output(self.mpc_c + ['-f', '%file%', 'playlist'])
        return format_mpc_output(output.decode())

    def get_playlist_positions(self):
        output = check_output(self.mpc_c + ['-f', '%file% %position%',
                                            'playlist'])
        lines = format_mpc_output(output.decode())
        positions = OrderedDict()
        for line in lines:
            song, position = line.rsplit(' ', 1)
            if song in positions:
                positions[song].append(int(position))
            else:
                positions[song] = [int(position)]
        return positions

    def get_current_song(self):
        return self.mpdclient.currentsong()['file']

# Database functions

    def get_all_songs(self):
        return list(self.get_all_songs_tags())

    def get_all_songs_tags(self, update=False):
        if self.all_songs_tags is not None and not update:
            pass
        elif is_cached('songs_tags') and not update:
            self.all_songs_tags = read_cache('songs_tags')
        else:
            self.all_songs_tags = OrderedDict()
            for song in self.mpdclient.listallinfo():
                if 'file' in song:
                    self.all_songs_tags[song['file']] = {
                        'artist': song.get('artist', ''),
                        'album': song.get('album', ''),
                        'title': song.get('title', ''),
                        'track': song.get('track', '')
                    }
            write_cache('songs_tags', self.all_songs_tags)
        return self.all_songs_tags

    def get_tag(self, filename, tag, empty=''):
        if tag in ('artist', 'album', 'title', 'track'):
            return self.get_all_songs_tags()[filename][tag] or empty
        else:
            return self.mpdclient.listallinfo(filename)[0].get(tag, empty)

    def get_tags(self, filename, tags_list=None, empty=''):
        if tags_list is None:
            tags_list = ('artist', 'album', 'title', 'track')
        return tuple([self.get_tag(filename, tag, empty) for tag in tags_list])

    def list_artists(self):
        output = check_output(self.mpc_c + ['list', 'artist'])
        return format_mpc_output(output.decode())

    def list_albums(self):
        albums = []
        for song in self.get_all_songs_tags().values():
            if song['album'] and song['artist']:
                albums.append((song['album'], song['artist']))
        return list(set(albums))

    def search(self, filtername, pattern):
        if filtername == 'extension':
            return [s for s in self.get_all_songs() if
                    s.lower().endswith(pattern.lower())]
        else:
            output = check_output(self.mpc_c + ['search', filtername,
                                                pattern])
            return format_mpc_output(output.decode())

    def search_multiple(self, **filters):
        query = []
        for filtername, pattern in filters.items():
            query.extend([filtername, pattern])
        return [song['file'] for song in self.mpdclient.search(*query)]

    def find(self, filtername, pattern):
        if filtername == 'extension':
            return [s for s in self.get_all_songs() if s.endswith(pattern)]
        else:
            return [song['file'] for song in
                    self.mpdclient.find(filtername, pattern)]

    def find_multiple(self, **filters):
        query = []
        for filtername, pattern in filters.items():
            query.extend([filtername, pattern])
        return [song['file'] for song in self.mpdclient.find(*query)]

# Stored playlists functions

    def get_stored_playlists(self):
        return [p['playlist'] for p in self.mpdclient.listplaylists()]

    def get_stored_playlists_info(self):
        return self.mpdclient.listplaylists()

    def get_stored_playlist_songs(self, name):
        return [song['file'] for song in self.mpdclient.listplaylistinfo(name)]

    def add_songs_stored_playlist(self, name, songs_files):
        for song_file in songs_files:
            self.mpdclient.playlistadd(name, song_file)

    def clear_stored_playlist(self, name):
        self.mpdclient.playlistclear(name)

# Misc methods

    def set_sort(self, songs_files):
        all_songs = self.get_all_songs()
        return OrderedSet([song for song in all_songs if song in songs_files])

    def update_cache(self):
        self.get_all_songs_tags(update=True)
