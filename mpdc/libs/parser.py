# coding: utf-8
import re
import sys
import random
from subprocess import check_output, CalledProcessError

from ply import lex
from ply import yacc

from mpdc.initialize import mpd, collections, enable_command
from mpdc.libs.utils import format_mpc_output, warning


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
        p[0] = set()
        if 'expression' in collection:
            p[0] |= p.parser.parse(collection['expression'],
                                   lexer=lex.lex(debug=0, reflags=re.UNICODE))
        if 'songs' in collection:
            p[0] |= set(collection['songs'])
        if enable_command and 'command' in collection:
            try:
                output = check_output(collection['command'], shell=True)
                p[0] |= set(format_mpc_output(output.decode()))
            except CalledProcessError:
                warning('Error while executing `command` in collection [%s]' %
                        p[1])
                sys.exit(0)

    elif p[1] == 'all':
        p[0] = set(mpd.get_all_songs())
    elif p[1] == 'c':
        p[0] = set(mpd.get_playlist_songs())
    elif p[1] == 'C':
        p[0] = set([mpd.get_current_song()])
    elif p[1] == 'A':
        c_song = mpd.get_current_song()
        p[0] = set(mpd.find('artist', mpd.get_tag(c_song, 'artist')))
    elif p[1] == 'B':
        c_song = mpd.get_current_song()
        p[0] = set(mpd.find_multiple(artist=mpd.get_tag(c_song, 'artist'),
                                     album=mpd.get_tag(c_song, 'album')))
    else:
        warning('Collection [%s] doesn\'t exist' % p[1])
        sys.exit(0)

def p_expression_filter(p):
    'expression : FILTER'
    p[0] = set(mpd.search(filters_alias[p[1][0]], p[1][2:-1]))

def p_expression_filter_exact(p):
    'expression : FILTER_EXACT'
    p[0] = set(mpd.find(filters_alias[(p[1][0]).lower()], p[1][2:-1]))

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
            p[0] = set(random.sample(p[1], int(modifier[1:])))
        except ValueError:
            p[0] = p[1]

    # N-random artists modifier - fixme: not really random
    elif re.match(r'^ra[0-9]+$', modifier):
        p[1] = list(p[1])
        random.shuffle(p[1])
        random_artists = set()
        for song in p[1]:
            if len(random_artists) < int(modifier[2:]):
                random_artists.add(mpd.get_tag(song, 'artist'))
            else:
                break
        matched_songs = []
        for artist in random_artists:
            matched_songs.extend(mpd.find('artist', artist))
        p[0] = set([song for song in p[1] if song in matched_songs])

    # N-random albums modifier - fixme: not really random
    elif re.match(r'^rb[0-9]+$', modifier):
        p[1] = list(p[1])
        random.shuffle(p[1])
        random_couples = []
        for song in p[1]:
            couple = {'album': mpd.get_tag(song, 'album'),
                      'artist': mpd.get_tag(song, 'artist')}
            if len(random_couples) < int(modifier[2:]):
                if couple not in random_couples:
                    random_couples.append(couple)
            else:
                break
        matched_songs = []
        for couple in random_couples:
            matched_songs.extend(mpd.find_multiple(album=couple['album'],
                                                   artist=couple['artist']))
        p[0] = set([song for song in p[1] if song in matched_songs])

    # N-minutes-long modifier
    elif re.match(r'^d[0-9]+$', modifier):
        total_duration = int(modifier[1:]) * 60
        d = 0
        p[0] = set()
        p[1] = list(p[1])
        random.shuffle(p[1])
        for song in p[1]:
            if d < total_duration:
                p[0].add(song)
                d += int(mpd.get_tag(song, 'time'))
            else:
                break

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
