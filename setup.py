
import certifi
from setuptools import setup

APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'icon.icns',
    'includes': ["tkinter","certifi","psutil"],
    'plist': {
        'CFBundleName': 'okr',
        'CFBundleDisplayName': 'okr',
        'CFBundleIdentifier': 'com.htmltoapk.okr',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        # Critical for SSL to work in bundled app
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True
        }
    },
    # This line tells py2app to find and bundle the SSL certificates
    'ssl_cert_file': certifi.where(),
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app']
)
