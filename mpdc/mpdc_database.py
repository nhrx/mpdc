# coding: utf-8
import argparse
from operator import itemgetter
from collections import Counter

from mpdc.initialize import mpd, collectionsmanager, lastfm, colors
from mpdc.libs.utils import repr_tags, info, warning, colorize, write_cache


# --------------------------------
# Program functions
# --------------------------------

def update(args):
    mpd.update_cache()
    write_cache('playlists', mpd.get_stored_playlists_info())
    collectionsmanager.feed(force=True)
    collectionsmanager.update_cache()


def check(args):
    songs = []
    for song, tags in mpd.get_all_songs_tags().items():
        missing_tags = [tag for tag, value in tags.items() if not value]
        if missing_tags:
            warning('You should tag [%s]' % colorize(song, colors[0]))
            print('missing tag(s): %s' % colorize(', '.join(missing_tags),
                                                  colors[1]))
        else:
            songs.append(tuple(sorted(tags.items())))
    duplicates = [dict(tags) for tags, nb in Counter(songs).items() if nb > 1]
    if duplicates:
        print('\nConflict(s) found:')
        print('------------------')
        for tags in duplicates:
            warning('Conflict with tags ' + colorize(repr_tags([tags['artist'],
                                                               tags['album'],
                                                               tags['title'],
                                                               tags['track']]),
                                                    colors[1]))
            files_matched = mpd.find_multiple(**tags)
            print('files matched: \n%s\n' % colorize('\n'.join(files_matched),
                                                     colors[0]))


def lastfm_update_artists(args):
    artists_tags = lastfm.artists_tags
    missing_artists = sorted(mpd.list_artists())
    if artists_tags:
        missing_artists = [artist for artist in missing_artists
                           if artist not in artists_tags]
    info('Will fetch datas for %s missing artist(s)' % len(missing_artists))
    for artist in missing_artists:
        print('Fetching %s' % artist)
        tags = lastfm.get_artist_tags(artist, update=True)
        if tags is not None:
            artists_tags[artist] = tags
    write_cache('artists_tags', artists_tags)


def lastfm_update_albums(args):
    albums_tags = lastfm.albums_tags
    missing_albums = sorted(mpd.list_albums(), key=itemgetter(1))
    if albums_tags:
        missing_albums = [album for album in missing_albums
                          if album not in albums_tags]
    info('Will fetch datas for %s missing album(s)' % len(missing_albums))
    for album, artist in missing_albums:
        print('Fetching %s / %s' % (artist, album))
        tags = lastfm.get_album_tags(album, artist, update=True)
        if tags is not None:
            albums_tags[(album, artist)] = tags
    write_cache('albums_tags', albums_tags)


# --------------------------------
# Commands parser
# --------------------------------

def main():
    argparser = argparse.ArgumentParser(add_help=False)
    subparsers = argparser.add_subparsers()

    update_p = subparsers.add_parser('update')
    update_p.set_defaults(func=update)

    check_p = subparsers.add_parser('check')
    check_p.set_defaults(func=check)

    lastfm_p = subparsers.add_parser('lastfm')
    lastfm_sp = lastfm_p.add_subparsers()

    lastfm_update_p = lastfm_sp.add_parser('update')
    lastfm_update_sp = lastfm_update_p.add_subparsers()

    lastfm_update_artists_p = lastfm_update_sp.add_parser('artists')
    lastfm_update_artists_p.set_defaults(func=lastfm_update_artists)

    lastfm_update_albums_p = lastfm_update_sp.add_parser('albums')
    lastfm_update_albums_p.set_defaults(func=lastfm_update_albums)

    args = argparser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
