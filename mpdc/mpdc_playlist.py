# coding: utf-8
import sys
import shlex
import argparse
import subprocess

from mpdc.initialize import mpd
from mpdc.libs.utils import input_box
from mpdc.libs.parser import parser


# --------------------------------
# Program functions
# --------------------------------

def add(args):
    songs = list(parser.parse(args.collection))
    if songs:
        mpd.add(songs)


def addp(args):
    songs = list(parser.parse(args.collection))
    if songs:
        mpd.add(songs)
        mpd.play_file(mpd.first_lately_added_song)


def insert(args):
    songs = list(parser.parse(args.collection))
    if songs:
        mpd.insert(songs)


def remove(args):
    songs = list(parser.parse(args.collection))
    if songs:
        mpd.remove(songs)


def keep(args):
    songs = parser.parse(args.collection)
    remove_songs = [s for s in mpd.get_playlist_songs() if s not in songs]
    if remove_songs:
        mpd.remove(remove_songs)


def replace(args):
    songs = list(parser.parse(args.collection))
    mpd.clear()
    if songs:
        mpd.add(songs)


def replacep(args):
    songs = list(parser.parse(args.collection))
    mpd.clear()
    if songs:
        mpd.add(songs)
        mpd.play()


def play(args):
    songs = parser.parse(args.collection)
    if songs:
        positions = mpd.get_playlist_positions()
        try:
            first_matched_song = next(s for s in positions if s in songs)
        except StopIteration:
            pass
        else:
            mpd.play(positions[first_matched_song][0])


def clear(args):
    mpd.clear()


def crop(args):
    mpd.crop()


def mpc(args):
    try:
        output = subprocess.check_output(mpd.mpc_c + shlex.split(args.command))
        print(output.decode().strip())
    except subprocess.CalledProcessError:
        pass


# --------------------------------
# Commands parser
# --------------------------------

def main():
    argparser = argparse.ArgumentParser(add_help=False)
    subparsers = argparser.add_subparsers()

    add_p = subparsers.add_parser('add')
    add_p.add_argument('collection')
    add_p.set_defaults(func=add)

    addp_p = subparsers.add_parser('addp')
    addp_p.add_argument('collection')
    addp_p.set_defaults(func=addp)

    insert_p = subparsers.add_parser('ins')
    insert_p.add_argument('collection')
    insert_p.set_defaults(func=insert)

    remove_p = subparsers.add_parser('rm')
    remove_p.add_argument('collection')
    remove_p.set_defaults(func=remove)

    keep_p = subparsers.add_parser('k')
    keep_p.add_argument('collection')
    keep_p.set_defaults(func=keep)

    replace_p = subparsers.add_parser('re')
    replace_p.add_argument('collection')
    replace_p.set_defaults(func=replace)

    replacep_p = subparsers.add_parser('rep')
    replacep_p.add_argument('collection')
    replacep_p.set_defaults(func=replacep)

    play_p = subparsers.add_parser('p')
    play_p.add_argument('collection')
    play_p.set_defaults(func=play)

    clear_p = subparsers.add_parser('clear')
    clear_p.set_defaults(func=clear)

    crop_p = subparsers.add_parser('crop')
    crop_p.set_defaults(func=crop)

    mpc_p = subparsers.add_parser(':')
    mpc_p.add_argument('command')
    mpc_p.set_defaults(func=mpc)

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
