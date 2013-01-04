# coding: utf-8
import os
import sys
import shlex
import curses
import argparse
import subprocess

from mpdc.initialize import mpd, collectionsmanager, collections, config, \
                            colors
from mpdc.libs.utils import input_box, write_cache, esc_quotes, info, \
                            warning, colorize
from mpdc.libs.parser import parser


def display_songs(filenames, path=None):
    if path is None:
        curses.setupterm()
        col = curses.tigetnum('cols')
        a_w = int(col * 0.25) - 1
        b_w = t_w = int(col * 0.375) - 1
        print('%s %s %s' % ('ARTIST'.ljust(a_w), 'TITLE'.ljust(t_w), 'ALBUM'))
        print('%s %s %s' % ('-' * a_w, '-' * b_w, '-' * t_w))
        current_song = mpd.get_current_song()
    for song in filenames:
        if path is None:
            bold = True if song == current_song else False
            tags = ('artist', 'title', 'album')
            artist, title, album = mpd.get_tags(song, tags, empty='<empty>')
            if len(artist) > a_w - 1:
                artist = artist[:a_w - 3] + '...'
            if len(title) > t_w - 1:
                title = title[:t_w - 3] + '...'
            if len(album) > b_w - 1:
                album = album[:b_w - 3] + '...'
            print('%s %s %s' % (colorize(artist.ljust(a_w), colors[0], bold),
                                colorize(title.ljust(t_w), colors[1], bold),
                                colorize(album, colors[2], bold)))
        else:
            print(os.path.join(path, song))


def format_alias(alias):
    if 'mpd_playlist' in collections[alias]:
        return colorize('(playlist) ', colors[1]) + alias
    elif 'sort' in collections[alias]:
        return colorize('@ ', colors[0]) + alias
    elif 'special' in collections[alias]:
        return colorize('# ', colors[0]) + alias
    else:
        return alias


# --------------------------------
# Program functions
# --------------------------------

def ls(args):
    if args.collection is None:
        for alias in collections:
            print(format_alias(alias))
    else:
        display_songs(parser.parse(args.collection), args.p)


def show(args):
    if args.alias in collections:
        if 'mpd_playlist' in collections[args.alias]:
            info('This collection is stored as a MPD playlist\n')
        elif 'sort' in collections[args.alias]:
            info('This collection is sorted automatically\n')
        elif 'special' in collections[args.alias]:
            info('This is a special collection\n')
        if 'expression' in collections[args.alias]:
            print(collections[args.alias]['expression'])
        if 'command' in collections[args.alias]:
            print('command: ' + collections[args.alias]['command'])
            print('--------\n')
        if 'songs' in collections[args.alias]:
            print('songs:')
            print('------')
            display_songs(collections[args.alias]['songs'], args.p)
    else:
        warning('Stored collection [%s] doesn\'t exist' % args.alias)


def check(args):
    # will print a warning if there's a problem
    print('Checking "songs" sections...')
    collectionsmanager.feed(force=True)
    for alias in collections:
        if 'mpd_playlist' not in collections[alias]:
            print('Checking collection [%s]...' % alias)
            parser.parse('"' + esc_quotes(alias) + '"')


def find(args):
    # assuming it's a file
    if args.pattern in mpd.get_all_songs():
        print('File found in:')
        print('--------------')
        for alias in collections:
            songs_c = parser.parse('"' + esc_quotes(alias) + '"')
            if args.pattern in songs_c:
                print(format_alias(alias))
    # assuming it's a collection
    else:
        songs = parser.parse(args.pattern)
        print('Collection is a subset of:')
        print('--------------------------')
        if songs:
            for alias in collections:
                songs_c = parser.parse('"' + esc_quotes(alias) + '"')
                if args.pattern != alias and songs.issubset(songs_c):
                    print(format_alias(alias))


def add_songs(args):
    songs = list(parser.parse(args.collection))
    if songs:
        collectionsmanager.add_songs(args.alias, songs)


def remove_songs(args):
    songs = list(parser.parse(args.collection))
    if songs:
        collectionsmanager.remove_songs(args.alias, songs)


def edit(args):
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR', 'nano')
    subprocess.call([editor, config['mpdc']['collections']])


# --------------------------------
# Commands parser
# --------------------------------

def main():
    argparser = argparse.ArgumentParser(add_help=False)
    subparsers = argparser.add_subparsers()

    listsongs_p = subparsers.add_parser('ls')
    listsongs_p.add_argument('collection', nargs='?')
    listsongs_p.add_argument('-p', nargs='?', const='')
    listsongs_p.set_defaults(func=ls)

    show_p = subparsers.add_parser('show')
    show_p.add_argument('alias')
    show_p.add_argument('-p', nargs='?', const='')
    show_p.set_defaults(func=show)

    find_p = subparsers.add_parser('find')
    find_p.add_argument('pattern')
    find_p.set_defaults(func=find)

    addsongs_p = subparsers.add_parser('addsongs')
    addsongs_p.add_argument('alias')
    addsongs_p.add_argument('collection')
    addsongs_p.set_defaults(func=add_songs)

    removesongs_p = subparsers.add_parser('rmsongs')
    removesongs_p.add_argument('alias')
    removesongs_p.add_argument('collection')
    removesongs_p.set_defaults(func=remove_songs)

    check_p = subparsers.add_parser('check')
    check_p.set_defaults(func=check)

    edit_p = subparsers.add_parser('edit')
    edit_p.set_defaults(func=edit)

    if len(sys.argv) == 1:
        cmd = input_box('mpdc-collections', 'Command for mpdc-collections:')
        if cmd is None or not cmd:
            sys.exit(0)
        if cmd.startswith('addsongs') or cmd.startswith('rmsongs'):
            lex = shlex.shlex(cmd, posix=True)
            lex.whitespace_split = True
            lex.commenters = ''
            cmd = [next(lex), next(lex), lex.instream.read()]
        else:
            cmd = cmd.split(' ', 1)
        args = argparser.parse_args(cmd)
    else:
        args = argparser.parse_args()

    args.func(args)

    if collectionsmanager.need_update:
        collectionsmanager.write_file()
        collectionsmanager.update_cache()
        write_cache('playlists', mpd.get_stored_playlists_info())

if __name__ == '__main__':
    main()
