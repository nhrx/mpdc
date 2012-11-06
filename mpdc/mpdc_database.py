# coding: utf-8
import argparse
from collections import Counter

from mpdc.initialize import mpd, collectionsmanager, colors
from mpdc.libs.utils import repr_tags, warning, colorize, write_cache


# --------------------------------
# Program functions
# --------------------------------

def update(args):
    mpd.update_cache()
    write_cache('playlists', mpd.get_stored_playlists_info())
    collectionsmanager.feed(force=True)
    collectionsmanager.update_cache()


def check(args):
    songs_tags = []
    for song in mpd.get_all_songs():
        tags = mpd.get_tags(song)
        if not all(tags):
            missing_tags = [tag for tag, value in
                            zip(('artist', 'album', 'title', 'track'), tags)
                            if not value]
            warning('You should tag [%s]' % colorize(song, colors[0]))
            print('missing tag(s): %s' % colorize(', '.join(missing_tags),
                                                    colors[1]))
        else:
            songs_tags.append(tags)

    not_unique = [song for song, nb in Counter(songs_tags).items() if nb > 1]
    if not_unique:
        print('\nConflict(s) found:')
        print('------------------')

        for tags in not_unique:
            files_matched = mpd.find_multiple(artist=tags[0],
                                              album=tags[1],
                                              title=tags[2],
                                              track=tags[3])
            warning('Conflict with ' + colorize(repr_tags(tags), colors[1]))
            print('files matched: \n%s\n' % colorize('\n'.join(files_matched),
                                                     colors[0]))


# --------------------------------
# Commands parser
# --------------------------------

def main():
    argparser = argparse.ArgumentParser(add_help=False)
    subparsers = argparser.add_subparsers()

    update_parser = subparsers.add_parser('update')
    update_parser.set_defaults(func=update)

    check_collisions_parser = subparsers.add_parser('check')
    check_collisions_parser.set_defaults(func=check)

    args = argparser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
