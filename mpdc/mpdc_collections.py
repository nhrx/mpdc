# coding: utf-8
import os
import sys
import shlex
import argparse
import subprocess

from mpdc.initialize import mpd, collectionsmanager, cache, colors, columns, \
                            enable_pager, pager
from mpdc.libs.utils import input_box, esc_quotes, info, warning, colorize, \
                            columns_width
from mpdc.libs.parser import parser


def display_songs(filenames, path=None, enable_pager=False):
    lines = []
    if path is None:
        c_w, t_w = columns_width(columns)
        header = ''
        for i, column in enumerate(columns):
            header += colorize(column.title().ljust(c_w[column]),
                               colors[i % len(colors)], True)
        if enable_pager:
            lines.append(header)
            lines.append('-' * t_w)
        else:
            print(header)
            print('—' * t_w)
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
                        tag = '{}:{:02}'.format(m, s)
                if len(tag) > c_w[column] - 1:
                    tag = tag[:c_w[column] - 2] + '…'
                row += colorize(tag.ljust(c_w[column]),
                                colors[i % len(colors)], bold)
            if enable_pager:
                lines.append(row)
            else:
                print(row)
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
    if 'mpd_playlist' in collectionsmanager.c[alias]:
        return colorize('(playlist) ', colors[0]) + alias
    elif 'sort' in collectionsmanager.c[alias]:
        return colorize('@ ', colors[0]) + alias
    elif 'special' in collectionsmanager.c[alias]:
        return colorize('# ', colors[0]) + alias
    return alias


# --------------------------------
# Program functions
# --------------------------------

def ls(args):
    if args.collection is None:
        for alias in collectionsmanager.c:
            print(format_alias(alias))
    else:
        songs = parser.parse(args.collection)
        display_songs(songs, args.f, (enable_pager or args.p) and not args.np)


def show(args):
    if args.alias in collectionsmanager.c:
        collection = collectionsmanager.c[args.alias]
        if 'mpd_playlist' in collection:
            info('This collection is stored as a MPD playlist\n')
        elif 'sort' in collection:
            info('This collection is sorted automatically\n')
        elif 'special' in collection:
            info('This is a special collection\n')
        if 'expression' in collection:
            print(collection['expression'])
        if 'command' in collection:
            print('command: ' + collection['command'])
            print('--------\n')
        if 'songs' in collection:
            print('songs:')
            print('------')
            display_songs(collection['songs'], args.f)
    else:
        warning('Stored collection [{}] does not exist'.format(args.alias))


def check(args):
    # will print a warning if there is a problem
    print('Checking "songs" sections...')
    collectionsmanager.feed(force=True)
    for alias, collection in collectionsmanager.c.items():
        if 'mpd_playlist' not in collection:
            print('Checking collection [{}]...'.format(alias))
            parser.parse('"' + esc_quotes(alias) + '"')


def find(args):
    # assuming it's a file
    if args.pattern in mpd.get_all_songs():
        print('File found in:')
        print('--------------')
        for alias in collectionsmanager.c:
            songs = parser.parse('"' + esc_quotes(alias) + '"')
            if args.pattern in songs:
                print(format_alias(alias))
    # assuming it's a collection
    else:
        songs = parser.parse(args.pattern)
        print('Collection is a subset of:')
        print('--------------------------')
        if songs:
            for alias in collectionsmanager.c:
                s = parser.parse('"' + esc_quotes(alias) + '"')
                if args.pattern.strip(' \'"') != alias and songs.issubset(s):
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
    subprocess.call(shlex.split(editor) + [collectionsmanager.path])
    check(args)


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
        cache.write('playlists', mpd.get_stored_playlists_info())

if __name__ == '__main__':
    main()
