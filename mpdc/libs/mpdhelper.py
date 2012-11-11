# coding: utf-8
from subprocess import check_output, Popen, PIPE, STDOUT

import mpd

from mpdc.libs.utils import is_cached, read_cache, write_cache, \
                            format_mpc_output


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
        songs_files = self.sort(songs_files)
        p = Popen(self.mpc_c + ['add'], stdin=PIPE, stderr=STDOUT)
        p.communicate(input=bytes('\n'.join(songs_files), 'utf-8'))
        self.first_lately_added_song = songs_files[0]

    def insert(self, songs_files):
        songs_files = self.sort(songs_files)
        p = Popen(self.mpc_c + ['insert'], stdin=PIPE, stderr=STDOUT)
        p.communicate(input=bytes('\n'.join(songs_files), 'utf-8'))
        self.first_lately_added_song = songs_files[0]

    def remove(self, songs_files):
        playlist_pos = self.get_playlist_positions()
        songs_ids = [str(playlist_pos[song]) for song in songs_files
                     if song in playlist_pos]
        p = Popen(self.mpc_c + ['del'], stdin=PIPE, stderr=STDOUT)
        p.communicate(input=bytes('\n'.join(songs_ids), 'utf-8'))

    def replace(self, songs_files):
        self.clear()
        self.add(songs_files)

    def play(self, song_position=1):
        # mpc starts at 1 whereas python-mpd2 starts at 0
        self.mpdclient.play(song_position - 1)

    def play_file(self, song_file):
        playlist_pos = self.get_playlist_positions()
        if song_file in playlist_pos:
            self.play(playlist_pos[song_file])

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
        positions = {}
        for line in lines:
            song, position = line.rsplit(' ', 1)
            positions[song] = int(position)
        return positions

    def get_current_song(self):
        return self.mpdclient.currentsong()['file']

# Database functions

    def get_all_songs(self, update=False):
        if self.all_songs is not None and not update:
            pass
        elif is_cached('allsongs') and not update:
            self.all_songs = read_cache('allsongs')
        else:
            output = check_output(self.mpc_c + ['listall'])
            self.all_songs = format_mpc_output(output.decode())
            write_cache('allsongs', self.all_songs)
        return self.all_songs

    def search(self, filter_name, pattern):
        if filter_name == 'extension':
            return [s for s in self.get_all_songs() if
                    s.lower().endswith(pattern.lower())]
        else:
            output = check_output(self.mpc_c + ['search', filter_name,
                                                pattern])
            return format_mpc_output(output.decode())

    def search_multiple(self, **tags):
        query = []
        for tag, value in tags.items():
            query.extend([tag, value])
        return [song['file'] for song in self.mpdclient.search(*query)]

    def find(self, filter_name, pattern):
        if filter_name == 'extension':
            return [s for s in self.get_all_songs() if s.endswith(pattern)]
        else:
            return [song['file'] for song in
                    self.mpdclient.find(filter_name, pattern)]

    def find_multiple(self, **tags):
        query = []
        for tag, value in tags.items():
            query.extend([tag, value])
        return [song['file'] for song in self.mpdclient.find(*query)]

    def get_tag(self, filename, tag):
        return self.mpdclient.listallinfo(filename)[0].get(tag, '')

    def get_tags(self, filename, tags_list=None):
        tags = self.mpdclient.listallinfo(filename)[0]
        if tags_list is None:
            tags_list = ('artist', 'album', 'title', 'track')
        return tuple([tags.get(tag, '') for tag in tags_list])

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

    def sort(self, songs_files):
        return [song for song in self.get_all_songs() if song in songs_files]

    def update_cache(self):
        self.get_all_songs(update=True)
