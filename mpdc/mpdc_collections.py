# coding: utf-8
import os
import sys
import shlex
import curses
import argparse
import subprocess

from mpdc.initialize import mpd, collectionsmanager, collections, config, \
                            colors, columns, enable_pager, pager
from mpdc.libs.utils import input_box, write_cache, esc_quotes, info, \
                            warning, colorize
from mpdc.libs.parser import parser


columns_w = {
    'artist': 1,
    'album': 1.5,
    'title': 1.5,
    'date': 0.25,
    'time': 0.25,
    'track': 0.25,
    'genre': 0.5,
    'filename': 2
}


def display_songs(filenames, path=None, enable_pager=False):
    lines = []
    if path is None:
        curses.setupterm()
        term_w = curses.tigetnum('cols')
        t_w = sum(columns_w[column] for column in columns)
        c_w = {}
        header = ''
        for i, column in enumerate(columns):
            c_w[column] = int(term_w * columns_w[column] / t_w)
            header += colorize(column.title().ljust(c_w[column] - 1),
                               colors[i % len(colors)], True) + ' '
        if enable_pager:
            lines.append(header.strip())
            lines.append('-' * term_w)
        else:
            print(header.strip())
            print('-' * term_w)
        current_song = mpd.get_current_song()
    for song in filenames:
        if path is None:
            bold = True if song == current_song else False
            row = ''
            for i, column in enumerate(columns):
                if column == 'filename':
                    tag = song
                else:
                    tag = mpd.get_tag(song, column, empty='<empty>')
                    if column == 'time':
                        m, s = divmod(int(tag), 60)
                        tag = '%d:%02d' % (m, s)
                if len(tag) > c_w[column] - 1:
                    tag = tag[:c_w[column] - 2] + '…'
                row += colorize(tag.ljust(c_w[column] - 1),
                                colors[i % len(colors)], bold) + ' '
            if enable_pager:
                lines.append(row.strip())
            else:
                print(row.strip())
        else:
            if enable_pager:
                lines.append(os.path.join(path, song))
            else:
                print(os.path.join(path, song))
    if enable_pager:
        pager_p = subprocess.Popen(shlex.split(pager), stdin=subprocess.PIPE)
        pager_p.stdin.write(bytes('\n'.join(lines), 'utf-8'))
        pager_p.stdin.close()
        pager_p.communicate()


def format_alias(alias):
    if 'mpd_playlist' in collections[alias]:
        return colorize('(playlist) ', colors[1 % len(colors)]) + alias
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
        display_songs(parser.parse(args.collection), args.f,
                     (enable_pager or args.p) and not args.np)


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
            display_songs(collections[args.alias]['songs'], args.f, False)
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
    listsongs_p.add_argument('-f', nargs='?', const='')
    listsongs_p.add_argument('--p', action='store_true')
    listsongs_p.add_argument('--np', action='store_true')
    listsongs_p.set_defaults(func=ls)

    show_p = subparsers.add_parser('show')
    show_p.add_argument('alias')
    show_p.add_argument('-f', nargs='?', const='')
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
