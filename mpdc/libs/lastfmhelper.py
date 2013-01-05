# coding: utf-8
import json
import socket
from operator import itemgetter
from time import sleep
from datetime import datetime, timedelta
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError

from mpdc.initialize import cache
from mpdc.libs.utils import similarity, warning


class LastfmHelper:

    api_key = '898b9a1eff53e869c384a4504cb2ca35'
    url = 'http://ws.audioscrobbler.com/2.0/?api_key=%s&format=json' % api_key
    delay = timedelta(0, 1)
    last_request = datetime.now() - delay

    methods = {
        'artist_tags': '&method=artist.gettoptags&artist={artist}'
                       '&autocorrect=1',
        'album_tags': '&method=album.gettoptags&artist={artist}'
                      '&album={album}&autocorrect=1'
    }

    min_similarity = 0.30

    bad_tags = ['beautiful', 'awesome', 'epic', 'masterpiece', 'favorite',
                'favourite', 'recommended', 'bands i', 'band i', 'best album',
                'my album', 'vinyl i', 'album i', 'albums i', 'album you',
                'albums you']

    def __init__(self):
        self.timeout = 0
        self.artists_tags = {}
        if cache.exists('artists_tags'):
            self.artists_tags = cache.read('artists_tags')
        self.albums_tags = {}
        if cache.exists('albums_tags'):
            self.albums_tags = cache.read('albums_tags')

    def request(self, method, **args):
        while LastfmHelper.last_request + LastfmHelper.delay > datetime.now():
            sleep(0.1)

        args_ = {key: quote(value) for (key, value) in args.items()}
        url = LastfmHelper.url + LastfmHelper.methods[method].format(**args_)

        try:
            raw_json = urlopen(url, timeout=15).read()
        except (socket.timeout, URLError):
            if self.timeout == 3:
                warning('Can\'t send the request after 4 attempts')
                self.timeout = 0
                return None
            self.timeout += 1
            warning('Time out... attempt n°' + str(self.timeout + 1))
            return self.request(method, **args)
        else:
            LastfmHelper.last_request = datetime.now()
            response = json.loads(raw_json.decode('utf-8'))
            if 'error' in response:
                warning('LastFM error: {}'.format(response['message']))
                return None
            self.timeout = 0
            return response

    def sanitize_tags(self, tags):
        if not isinstance(tags, list):
            tags = [tags]
        tags_sanitized = {}
        for tag in tags:
            if all(bad not in tag['name'].lower() for bad in
               LastfmHelper.bad_tags) and int(tag['count']):
                tags_sanitized[tag['name'].lower()] = int(tag['count'])
        return tags_sanitized

    def get_artist_tags(self, artist, update=False):
        if not update:
            if not self.artists_tags:
                warning('You should update the LastFM database')
            elif artist in self.artists_tags:
                return self.artists_tags[artist]
            return {}
        else:
            data = self.request('artist_tags', artist=artist)
            if data is not None:
                if 'tag' in data.get('toptags', {}):
                    return self.sanitize_tags(data['toptags']['tag'])
                return {}
            return None

    def get_album_tags(self, album, artist, update=False):
        if not update:
            if not self.albums_tags:
                warning('You should update the LastFM database')
            elif (album, artist) in self.albums_tags:
                return self.albums_tags[(album, artist)]
            return {}
        else:
            data = self.request('album_tags', artist=artist, album=album)
            if data is not None:
                if 'tag' in data.get('toptags', {}):
                    return self.sanitize_tags(data['toptags']['tag'])
                return {}
            return None

    def search_artists(self, pattern):
        for artist, tags in self.artists_tags.items():
            if any(pattern in tag for tag in tags):
                yield artist

    def find_artists(self, pattern):
        for artist, tags in self.artists_tags.items():
            if pattern in tags:
                yield artist

    def search_albums(self, pattern):
        for album, tags in self.albums_tags.items():
            if any(pattern in tag for tag in tags):
                yield album

    def find_albums(self, pattern):
        for album, tags in self.albums_tags.items():
            if pattern in tags:
                yield album

    def get_similar_artists(self, query):
        if not self.artists_tags:
            warning('You should update the LastFM database')
            return
        scores = {}
        for artist, tags in self.artists_tags.items():
            if tags:
                score = similarity(tags, query)
                if score > LastfmHelper.min_similarity:
                    scores[artist] = score
        scores_desc = sorted(scores.items(), key=itemgetter(1), reverse=True)
        for match in scores_desc:
            yield match

    def get_similar_albums(self, query):
        if not self.albums_tags:
            warning('You should update the LastFM database')
            return
        scores = {}
        for (album, artist), tags in self.albums_tags.items():
            if tags:
                score = similarity(tags, query)
                if score > LastfmHelper.min_similarity:
                    scores[(album, artist)] = score
        scores_desc = sorted(scores.items(), key=itemgetter(1), reverse=True)
        for match in scores_desc:
            yield match
