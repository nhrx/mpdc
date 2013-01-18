# coding: utf-8
import operator
import argparse
from collections import Counter

from mpdc.initialize import mpd, collectionsmanager, lastfm, cache, colors
from mpdc.libs.utils import repr_tags, info, warning, colorize


# --------------------------------
# Program functions
# --------------------------------

def update(args):
    mpd.update_cache()
    cache.write('playlists', mpd.get_stored_playlists_info())
    collectionsmanager.feed(force=True)
    collectionsmanager.update_cache()


def check(args):
    songs = []
    for song, tags in mpd.get_all_songs_tags().items():
        missing_tags = [tag for tag, value in tags.items() if not value]
        if missing_tags:
            warning(colorize(song, colors[0]))
            print('missing tag(s): ' + colorize(', '.join(missing_tags),
                                                colors[1 % len(colors)]))
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
                                                     colors[1 % len(colors)]))
            files_matched = mpd.find_multiple(**tags)
            print('files matched:\n' + colorize('\n'.join(files_matched),
                                                colors[0]))


def lastfm_update_artists(args):
    tags = lastfm.artists_tags
    artists = sorted(mpd.list_artists())
    extra_artists = [artist for artist in tags if artist not in artists]
    info('{} extra artist(s)'.format(len(extra_artists)))
    for artist in extra_artists:
        del tags[artist]
    if tags:
        missing_artists = [artist for artist in artists if artist not in tags]
    else:
        missing_artists = artists
    info('{} missing artist(s)'.format(len(missing_artists)))
    for artist in missing_artists:
        print('Fetching {}'.format(artist))
        tags[artist] = lastfm.get_artist_tags(artist, update=True)
    cache.write('artists_tags', tags)


def lastfm_update_albums(args):
    tags = lastfm.albums_tags
    albums = sorted(mpd.list_albums(), key=operator.itemgetter(1))
    extra_albums = [album for album in tags if album not in albums]
    info('{} extra album(s)'.format(len(extra_albums)))
    for album in extra_albums:
        del tags[album]
    if tags:
        missing_albums = [album for album in albums if album not in tags]
    else:
        missing_albums = albums
    info('{} missing album(s)'.format(len(missing_albums)))
    for album, artist in missing_albums:
        print('Fetching {} / {}'.format(artist, album))
        tags[(album, artist)] = lastfm.get_album_tags(album,
                                                      artist, update=True)
    cache.write('albums_tags', tags)


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
