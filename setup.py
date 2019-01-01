import setuptools

from gwe.conf import APP_PACKAGE_NAME, APP_VERSION, APP_SOURCE_URL, APP_AUTHOR, APP_AUTHOR_EMAIL, APP_MAIN_UI_NAME, \
    APP_EDIT_FAN_PROFILE_UI_NAME, APP_PREFERENCES_UI_NAME, APP_DESCRIPTION

# with open('README.md', 'r', encoding='utf-8') as fh:
#     long_description = (fh.read().split('<!-- stop here for PyPI -->', 1)[0]
#                         + 'Check the project page page for more information.')

setuptools.setup(
    name=APP_PACKAGE_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    # long_description=long_description,
    # long_description_content_type='text/markdown',
    url=APP_SOURCE_URL,
    author=APP_AUTHOR,
    author_email=APP_AUTHOR_EMAIL,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Topic :: Desktop Environment :: Gnome',
        'Topic :: System :: Hardware',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities',
    ],
    keywords='nvidia overclock',
    packages=setuptools.find_packages(),
    package_data={
        APP_PACKAGE_NAME: [
            'data/gwe.svg',
            'data/gwe-symbolic.svg',
            'data/' + APP_MAIN_UI_NAME,
            'data/' + APP_EDIT_FAN_PROFILE_UI_NAME,
            'data/' + APP_PREFERENCES_UI_NAME,
        ],

    },
    project_urls={
        'Source': APP_SOURCE_URL,
        'Tracker': APP_SOURCE_URL + '/issues',
        'Changelog': '{}/blob/{}/CHANGELOG.md'.format(APP_SOURCE_URL, APP_VERSION),
        'Documentation': '{}/blob/{}/README.md'.format(APP_SOURCE_URL, APP_VERSION),

    },
    install_requires=[
        'injector==0.14.1',
        'matplotlib==3.0.2',
        'peewee==3.8.0',
        'pygobject',
        'pyxdg',
        'requests',
        'rx==1.6.1',
    ],
    python_requires='~=3.6',
    entry_points={
        'console_scripts': [
            'gwe=gwe.main:main',
        ],
    },
)
