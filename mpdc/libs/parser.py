# coding: utf-8
import re
import sys
import random
from collections import defaultdict
from subprocess import check_output, CalledProcessError

from ply import lex
from ply import yacc

from mpdc.initialize import mpd, collections, lastfm, enable_command
from mpdc.libs.utils import format_mpc_output, warning, OrderedSet


filters_alias = {
    'a': 'artist',
    'b': 'album',
    't': 'title',
    'n': 'track',
    'g': 'genre',
    'd': 'date',
    'c': 'composer',
    'p': 'performer',
    'f': 'filename',
    'e': 'extension',
    'x': 'any'
}


# --------------------------------
# Lexer
# --------------------------------

tokens = (
    'FILTER', 'FILTER_EXACT', 'MODIFIER', 'COLLECTION',
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
    r'([abtngdcpfex]{1}"(?:[^"\\]|\\.)*") |' \
    r'([abtngdcpfex]{1}\'(?:[^\'\\]|\\.)*\')'
    if t.value[1] == "'":
        t.value = t.value.replace(r"\'", "'")
    else:
        t.value = t.value.replace(r'\"', '"')
    return t

def t_FILTER_EXACT(t):
    r'([ABTNGDCPFEX]{1}"(?:[^"\\]|\\.)*") |' \
    r'([ABTNGDCPFEX]{1}\'(?:[^\'\\]|\\.)*\')'
    if t.value[1] == "'":
        t.value = t.value.replace(r"\'", "'")
    else:
        t.value = t.value.replace(r'\"', '"')
    return t

def t_COLLECTION(t):
    r'\w+ |' \
    r'"((?:[^"\\]|\\.)*") |' \
    r'\'((?:[^\'\\]|\\.)*\')'
    if t.value[0] == '"':
        t.value = t.value.replace(r'\"', '"')[1:-1]
    elif t.value[0] == "'":
        t.value = t.value.replace(r"\'", "'")[1:-1]
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')

def t_error(t):
    warning('Illegal character `%s`' % t.value[0])
    sys.exit(0)

t_ignore = ' \t'

lexer = lex.lex(debug=0, reflags=re.UNICODE)


# --------------------------------
# Parser
# --------------------------------

precedence = (
    ('left', 'UNION', 'INTERSECTION', 'COMPLEMENT', 'SYMMETRIC_DIFFERENCE'),
    ('left', 'MODIFIER'),
)

def p_expression_collection(p):
    'expression : COLLECTION'
    if p[1] in collections:
        collection = collections[p[1]]
        p[0] = OrderedSet()
        if 'expression' in collection:
            p[0] |= p.parser.parse(collection['expression'],
                                   lexer=lex.lex(debug=0, reflags=re.UNICODE))
        if 'songs' in collection:
            p[0] |= OrderedSet(collection['songs'])
        if enable_command and 'command' in collection:
            try:
                output = check_output(collection['command'], shell=True)
                p[0] |= OrderedSet(format_mpc_output(output.decode()))
            except CalledProcessError:
                warning('Error while executing `command` in collection [%s]' %
                        p[1])
                sys.exit(0)

    elif p[1] == 'all':
        p[0] = OrderedSet(mpd.get_all_songs())
    elif p[1] == 'c':
        p[0] = OrderedSet(mpd.get_playlist_songs())
    elif p[1] == 'C':
        p[0] = OrderedSet([mpd.get_current_song()])
    elif p[1] == 'A':
        c_song = mpd.get_current_song()
        p[0] = OrderedSet(mpd.find('artist', mpd.get_tag(c_song, 'artist')))
    elif p[1] == 'B':
        c_song = mpd.get_current_song()
        p[0] = OrderedSet(mpd.find_multiple(artist=mpd.get_tag(c_song, 'artist'),
                                     album=mpd.get_tag(c_song, 'album')))
    else:
        warning('Collection [%s] doesn\'t exist' % p[1])
        sys.exit(0)

def p_expression_filter(p):
    'expression : FILTER'
    p[0] = OrderedSet(mpd.search(filters_alias[p[1][0]], p[1][2:-1]))

def p_expression_filter_exact(p):
    'expression : FILTER_EXACT'
    p[0] = OrderedSet(mpd.find(filters_alias[(p[1][0]).lower()], p[1][2:-1]))

def p_expression_operations(p):
    '''expression : expression UNION expression
                  | expression COMPLEMENT expression
                  | expression INTERSECTION expression
                  | expression SYMMETRIC_DIFFERENCE expression'''
    if p[2] == '+':
        p[0] = p[1] | p[3]
    elif p[2] == '-':
        p[0] = p[1] - p[3]
    elif p[2] == '.':
        p[0] = p[1] & p[3]
    elif p[2] == '%':
        p[0] = p[1] ^ p[3]

def p_expression_modifier(p):
    'expression : expression MODIFIER'
    modifier = (p[2][1:]).lstrip()

    # N-random songs modifier
    if re.match(r'^r[0-9]+$', modifier):
        try:
            p[0] = OrderedSet(random.sample(p[1], int(modifier[1:])))
        except ValueError:
            p[0] = p[1]

    # N-random artists modifier
    elif re.match(r'^ra[0-9]+$', modifier):
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
        albums = OrderedSet()
        for song in p[1]:
            albums.add(mpd.get_tags(song, ('album', 'artist')))
        try:
            r_albums = OrderedSet(random.sample(albums, int(modifier[2:])))
        except ValueError:
            p[0] = p[1]
        else:
            songs = []
            for album, artist in r_albums:
                songs.extend(mpd.find_multiple(album=album, artist=artist))
            p[0] = OrderedSet([song for song in p[1] if song in songs])

    # N-minutes-long modifier
    elif re.match(r'^d[0-9]+$', modifier):
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
        limit = int((modifier[3:] if include else modifier[2:]))
        w_tags = defaultdict(int)
        for song in p[1]:
            tags = lastfm.get_artist_tags(mpd.get_tag(song, 'artist'))
            for tag in tags:
                w_tags[tag] += tags[tag]
        if not w_tags:
            p[0] = p[1] if include else OrderedSet()
        else:
            songs = []
            similar_artists = lastfm.get_similar_artists(w_tags)
            for artist, score in similar_artists:
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
        limit = int((modifier[3:] if include else modifier[2:]))
        w_tags = defaultdict(int)
        for song in p[1]:
            tags = lastfm.get_album_tags(mpd.get_tag(song, 'album'),
                                         mpd.get_tag(song, 'artist'))
            for tag in tags:
                w_tags[tag] += tags[tag]
        if not w_tags:
            p[0] = p[1] if include else OrderedSet()
        else:
            songs = []
            for (album, artist), score in lastfm.get_similar_albums(w_tags):
                if not limit:
                    break
                matched_songs = mpd.find_multiple(album=album, artist=artist)
                if not include:
                    matched_songs = OrderedSet(matched_songs) - p[1]
                if matched_songs:
                    songs.extend(matched_songs)
                    limit -= 1
            p[0] = OrderedSet(songs)

    else:
        warning('Modifier [%s] doesn\'t exist' % modifier)
        sys.exit(0)

def p_expression_parenthesized(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_error(t):
    warning('Syntax error')
    sys.exit(0)

parser = yacc.yacc(debug=0, outputdir='/tmp/')
# parser.parse(<collection>) will return a set of filenames
