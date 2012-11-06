# coding: utf-8
try:
    from setuptools import setup, find_packages
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup, find_packages

import os


def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


if which('mpc') is None or which('zenity') is None:
    print('Please install mpc and zenity before installing MPDC.')

else:
    setup(
        name='MPDC',
        version='1.0rc1',
        license='MIT',
        description='A XMMS2-like collections system for MPD',
        author='nhrx.org',
        url='http://nhrx.org/mpdc',
        packages=find_packages(),
        entry_points={
              'console_scripts': [
                  'mpdc-playlist = mpdc.mpdc_playlist:main',
                  'mpdc-collections = mpdc.mpdc_collections:main',
                  'mpdc-database = mpdc.mpdc_database:main',
                  'mpdc-configure = mpdc.mpdc_configure:main'
              ]
        },
        install_requires=['ply >= 3.4', 'python-mpd2 >= 0.4.0']
    )
