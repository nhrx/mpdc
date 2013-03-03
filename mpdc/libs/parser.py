# coding: utf-8
import re
import sys
import random
import subprocess
import collections

from ply import lex
from ply import yacc

from mpdc.initialize import mpd, collectionsmanager, lastfm, enable_command
from mpdc.libs.utils import format_mpc_output, warning, OrderedSet


# --------------------------------
# Lexer
# --------------------------------

tokens = (
    'FILTER', 'MODIFIER', 'COLLECTION',
    'UNION', 'INTERSECTION', 'COMPLEMENT', 'SYMMETRIC_DIFFERENCE',
    'LPAREN', 'RPAREN',
)


t_UNION = r'\+'
t_INTERSECTION = r'\.'
t_COMPLEMENT = r'\-'
t_SYMMETRIC_DIFFERENCE = r'%'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_MODIFIER = r'\|[ ]*\w+'


def t_FILTER(t):
    r'([abtngdcpfexlr]{1,2}"(?:[^"\\]|\\.)*") |' \
    r'([abtngdcpfexlr]{1,2}\'(?:[^\'\\]|\\.)*\')'
    delimiter = next(c for c in t.value if c in '"\'')
    t.value = t.value.replace('\\' + delimiter, delimiter)
    return t


def t_COLLECTION(t):
    r'\w+ |' \
    r'"((?:[^"\\]|\\.)*") |' \
    r'\'((?:[^\'\\]|\\.)*\')'
    if t.value[0] == '"':
        t.value = t.value.replace('\"', '"')[1:-1]
    elif t.value[0] == "'":
        t.value = t.value.replace("\'", "'")[1:-1]
    return t


def t_error(t):
    warning('Illegal character `{}`'.format(t.value[0]))
    sys.exit(0)


t_ignore = ' \t\n'

lexer = lex.lex(debug=0, reflags=re.UNICODE|re.IGNORECASE)


# --------------------------------
# Parser
# --------------------------------

precedence = (
    ('left', 'MODIFIER'),
    ('left', 'UNION', 'INTERSECTION', 'COMPLEMENT', 'SYMMETRIC_DIFFERENCE'),
)

filters_alias = {
    'a': 'artist',
    'b': 'album',
    'ab': 'albumartist',
    't': 'title',
    'n': 'track',
    'g': 'genre',
    'd': 'date',
    'c': 'composer',
    'p': 'performer',
    'f': 'filename',
    'e': 'extension',
    'x': 'any',
    'la': 'lastfm_a',
    'lb': 'lastfm_b'
}


def exclude_songs(songs):
    if 'special' in collectionsmanager.c.get('exclude', {}):
        ex_songs = parser.parse('exclude',
                   lexer=lex.lex(debug=0, reflags=re.UNICODE|re.IGNORECASE))
        return songs - ex_songs
    return songs


def p_expression_collection(p):
    'expression : COLLECTION'
    p[0] = OrderedSet()
    if p[1] in collectionsmanager.c:
        collection = collectionsmanager.c[p[1]]
        if 'expression' in collection:
            p[0] |= parser.parse(collection['expression'],
                    lexer=lex.lex(debug=0, reflags=re.UNICODE|re.IGNORECASE))
        if 'songs' in collection:
            p[0] |= OrderedSet(collection['songs'])
        if enable_command and 'command' in collection:
            try:
                output = subprocess.check_output(collection['command'],
                                                 shell=True)
                p[0] |= OrderedSet(format_mpc_output(output.decode()))
            except subprocess.CalledProcessError:
                warning('Error while executing `command` in collection [{}]'.
                        format(p[1]))
                sys.exit(0)
        if 'sort' in collection:
            p[0] = mpd.set_sort(p[0])
    elif p[1] == 'all':
        p[0] = OrderedSet(mpd.get_all_songs())
    elif p[1] == 'c':
        p[0] = OrderedSet(mpd.get_playlist_songs())
    elif p[1] == 'C':
        c_song = mpd.get_current_song()
        if c_song is not None:
            p[0] = OrderedSet([c_song])
    elif p[1] == 'A':
        c_song = mpd.get_current_song()
        if c_song is not None:
            p[0] = OrderedSet(mpd.find('artist',
                                       mpd.get_tag(c_song, 'artist')))
    elif p[1] == 'B':
        c_song = mpd.get_current_song()
        if c_song is not None:
            p[0] = OrderedSet(mpd.find_multiple(
                              albumartist=mpd.get_tag(c_song, 'albumartist'),
                              album=mpd.get_tag(c_song, 'album')))
            if not p[0]:
                p[0] = OrderedSet(mpd.find_multiple(
                                  artist=mpd.get_tag(c_song, 'artist'),
                                  album=mpd.get_tag(c_song, 'album')))
    else:
        warning('Collection [{}] does not exist'.format(p[1]))
        sys.exit(0)


def p_expression_filter(p):
    'expression : FILTER'
    exact = True if p[1][0].isupper() else False
    alias = (p[1][0] if p[1][1] in '"\'' else p[1][0:2]).lower()
    name = filters_alias.get(alias, '')
    pattern = p[1][2:-1] if p[1][1] in '"\'' else p[1][3:-1]
    if not name:
        warning('Filter [{}] does not exist'.format(alias))
        sys.exit(0)
    if name == 'lastfm_a':
        p[0] = OrderedSet()
        if exact:
            artists = lastfm.find_artists(pattern)
        else:
            artists = lastfm.search_artists(pattern)
        for artist in artists:
            p[0] |= mpd.find('artist', artist)
    elif name == 'lastfm_b':
        p[0] = OrderedSet()
        if exact:
            albums = lastfm.find_albums(pattern)
        else:
            albums = lastfm.search_albums(pattern)
        for album, artist in albums:
            matched_songs = mpd.find_multiple(albumartist=artist, album=album)
            if not matched_songs:
                matched_songs = mpd.find_multiple(artist=artist, album=album)
            p[0] |= matched_songs
        p[0] = mpd.set_sort(p[0])
    elif exact:
        p[0] = OrderedSet(mpd.find(name, pattern))
    else:
        p[0] = OrderedSet(mpd.search(name, pattern))


def p_expression_operations(p):
    '''expression : expression UNION expression
                  | expression INTERSECTION expression
                  | expression COMPLEMENT expression
                  | expression SYMMETRIC_DIFFERENCE expression'''
    if p[2] == '+':
        p[0] = p[1] | p[3]
    elif p[2] == '.':
        p[0] = p[1] & p[3]
    elif p[2] == '-':
        p[0] = p[1] - p[3]
    elif p[2] == '%':
        p[0] = p[1] ^ p[3]


def p_expression_modifier(p):
    'expression : expression MODIFIER'
    modifier = (p[2][1:]).lstrip()

    # Sorting modifier
    if modifier == 's':
        p[0] = mpd.set_sort(p[1])

    # N-random songs modifier
    elif re.match(r'^r[0-9]+$', modifier):
        p[1] = exclude_songs(p[1])
        try:
            p[0] = OrderedSet(random.sample(p[1], int(modifier[1:])))
        except ValueError:
            p[0] = p[1]

    # N-random artists modifier
    elif re.match(r'^ra[0-9]+$', modifier):
        p[1] = exclude_songs(p[1])
        artists = OrderedSet()
        for song in p[1]:
            artists.add(mpd.get_tag(song, 'artist'))
        try:
            r_artists = OrderedSet(random.sample(artists, int(modifier[2:])))
        except ValueError:
            p[0] = p[1]
        else:
            songs = []
            for artist in r_artists:
                songs.extend(mpd.find('artist', artist))
            p[0] = OrderedSet([song for song in p[1] if song in songs])

    # N-random albums modifier
    elif re.match(r'^rb[0-9]+$', modifier):
        p[1] = exclude_songs(p[1])
        albums = OrderedSet()
        for song in p[1]:
            albums.add(mpd.get_tags(song, ('album', 'albumartist')))
        try:
            r_albums = OrderedSet(random.sample(albums, int(modifier[2:])))
        except ValueError:
            p[0] = p[1]
        else:
            songs = []
            for album, artist in r_albums:
                matched_songs = mpd.find_multiple(album=album,
                                                  albumartist=artist)
                if not matched_songs:
                    matched_songs = mpd.find_multiple(album=album,
                                                      artist=artist)
                songs.extend(matched_songs)
            p[0] = OrderedSet([song for song in p[1] if song in songs])

    # N-minutes-long modifier
    elif re.match(r'^d[0-9]+$', modifier):
        p[1] = exclude_songs(p[1])
        total_duration = int(modifier[1:]) * 60
        d = 0
        p[0] = OrderedSet()
        p[1] = list(p[1])
        random.shuffle(p[1])
        for song in p[1]:
            if d < total_duration:
                p[0].add(song)
                d += int(mpd.get_tag(song, 'time'))
            else:
                break

    # N-similar artists modifier
    elif re.match(r'^i?sa[0-9]+$', modifier):
        include = True if modifier[0] == 'i' else False
        limit = int(modifier[3:] if include else modifier[2:])
        w_tags = collections.defaultdict(int)
        for song in p[1]:
            tags = lastfm.get_artist_tags(mpd.get_tag(song, 'artist'))
            for tag, w in tags.items():
                w_tags[tag] += w
        if not w_tags:
            p[0] = p[1] if include else OrderedSet()
        else:
            songs = []
            for artist, score in lastfm.get_similar_artists(w_tags):
                if not limit:
                    break
                matched_songs = mpd.find('artist', artist)
                if not include:
                    matched_songs = OrderedSet(matched_songs) - p[1]
                if matched_songs:
                    songs.extend(matched_songs)
                    limit -= 1
            p[0] = OrderedSet(songs)

    # N-similar albums modifier
    elif re.match(r'^i?sb[0-9]+$', modifier):
        include = True if modifier[0] == 'i' else False
        limit = int(modifier[3:] if include else modifier[2:])
        w_tags = collections.defaultdict(int)
        for song in p[1]:
            tags = lastfm.get_album_tags(mpd.get_tag(song, 'album'),
                                         mpd.get_tag(song, 'albumartist'))
            for tag, w in tags.items():
                w_tags[tag] += w
        if not w_tags:
            p[0] = p[1] if include else OrderedSet()
        else:
            songs = []
            for (album, artist), score in lastfm.get_similar_albums(w_tags):
                if not limit:
                    break
                matched_songs = mpd.find_multiple(album=album,
                                                  albumartist=artist)
                if not matched_songs:
                    matched_songs = mpd.find_multiple(album=album,
                                                      artist=artist)
                if not include:
                    matched_songs = OrderedSet(matched_songs) - p[1]
                if matched_songs:
                    songs.extend(matched_songs)
                    limit -= 1
            p[0] = OrderedSet(songs)

    else:
        warning('Modifier [{}] does not exist'.format(modifier))
        sys.exit(0)


def p_expression_parenthesized(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]


def p_error(t):
    warning('Syntax error')
    sys.exit(0)


parser = yacc.yacc(debug=0, outputdir='/tmp/')
# parser.parse(<collection>) will return a set of filenames
