# coding: utf-8
import sys
import argparse
from subprocess import check_output

from mpdc.initialize import mpd
from mpdc.libs.utils import input_box
from mpdc.libs.parser import parser


# --------------------------------
# Program functions
# --------------------------------

def add(args):
    songs = parser.parse(args.collection)
    if songs:
        mpd.add(songs)


def addp(args):
    songs = parser.parse(args.collection)
    if songs:
        mpd.add(songs)
        mpd.play_file(mpd.first_lately_added_song)


def insert(args):
    songs = parser.parse(args.collection)
    if songs:
        mpd.insert(songs)


def remove(args):
    songs = parser.parse(args.collection)
    if songs:
        mpd.remove(songs)


def replace(args):
    songs = parser.parse(args.collection)
    if songs:
        mpd.replace(songs)
    else:
        mpd.clear()


def replacep(args):
    songs = parser.parse(args.collection)
    if songs:
        mpd.replace(songs)
        mpd.play()
    else:
        mpd.clear()


def play(args):
    songs = mpd.sort(parser.parse(args.collection))
    if songs:
        playlist_pos = mpd.get_playlist_positions()
        try:
            first_matched_song = next((s for s in songs if s in playlist_pos))
        except StopIteration:
            pass
        else:
            mpd.play(playlist_pos[first_matched_song])


def clear(args):
    mpd.clear()


def crop(args):
    mpd.crop()


def mpc(args):
    output = check_output('%s %s' % (mpd.mpc_c_str, args.command), shell=True)
    print(output.decode().strip())


# --------------------------------
# Commands parser
# --------------------------------

def main():
    argparser = argparse.ArgumentParser(add_help=False)
    subparsers = argparser.add_subparsers()

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('collection')
    add_parser.set_defaults(func=add)

    addp_parser = subparsers.add_parser('addp')
    addp_parser.add_argument('collection')
    addp_parser.set_defaults(func=addp)

    insert_parser = subparsers.add_parser('ins')
    insert_parser.add_argument('collection')
    insert_parser.set_defaults(func=insert)

    remove_parser = subparsers.add_parser('rm')
    remove_parser.add_argument('collection')
    remove_parser.set_defaults(func=remove)

    replace_parser = subparsers.add_parser('re')
    replace_parser.add_argument('collection')
    replace_parser.set_defaults(func=replace)

    replacep_parser = subparsers.add_parser('rep')
    replacep_parser.add_argument('collection')
    replacep_parser.set_defaults(func=replacep)

    play_parser = subparsers.add_parser('p')
    play_parser.add_argument('collection')
    play_parser.set_defaults(func=play)

    clear_parser = subparsers.add_parser('clear')
    clear_parser.set_defaults(func=clear)

    crop_parser = subparsers.add_parser('crop')
    crop_parser.set_defaults(func=crop)

    mpc_parser = subparsers.add_parser(':')
    mpc_parser.add_argument('command')
    mpc_parser.set_defaults(func=mpc)

    if len(sys.argv) == 1:
        cmd = input_box('mpdc-playlist', 'Command for mpdc-playlist:')
        if cmd is None or not cmd:
            sys.exit(0)
        if cmd[0] == ':' and cmd[1] != ' ':
            cmd = ': ' + cmd[1:]
        args = argparser.parse_args(cmd.split(' ', 1))

    else:
        args = argparser.parse_args()

    args.func(args)

if __name__ == '__main__':
    main()
