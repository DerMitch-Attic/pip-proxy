#!/usr/bin/env python
"""
    PIP Proxy
    ~~~~~~~~~

    A simple caching proxy server for pip. Proxies and rewrites any requests
    to PyPi and caches them. It never redirects clients to PyPi like other
    solutions, so your pip clients don't need a direct internet connection.

    It's currently in beta and may contain awful bugs, use it at your own
    risk!

    :copyright: Michael Mayr <michael@michfrm.net>
    :licence: MIT License
"""

from __future__ import print_function

import os
import pickle
import shutil
import tempfile
from hashlib import md5
from ConfigParser import SafeConfigParser

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import requests
from tornado import web, ioloop, autoreload, options, httpclient

config = SafeConfigParser()
config.read("config.ini")
getconfig = lambda key: config.get('pipproxy', key)

def downloader(request, url, filename):
    """Gevent worker: Downloads files, streams them back to the client
       and saves them to a local file.
    """
    print("[downloader] Begin:", url)
    req = requests.get(url, stream=True)
    if not req.ok:
        request.write_error(req.status_code)
        return

    dirname = os.path.dirname(filename)
    if not os.path.isdir(dirname):
        print("[downloader] Creating directories:", dirname)
        os.makedirs(dirname)

    print("[downloader] setting headers")
    header = 'attachment; filename="{}"'.format(os.path.basename(url))
    request.set_header('Content-Disposition', header)
    request.set_header('Content-Type', req.headers['Content-Type'])
    if req.headers['Content-Length']:
        request.set_header('Content-Length', req.headers['Content-Length'])

    print("[downloader] iterating response")
    tmp_file = tempfile.NamedTemporaryFile()

    with open(tmp_file.name, "wb") as f:
        for chunk in req.iter_content(chunk_size=10 * 1024):
            request.write(chunk)
            f.write(chunk)

    print("[downloader] Moving temporary file")
    shutil.copyfile(tmp_file.name, filename)

    print("[downloader] Done!")
    request.finish()

def looks_like_a_file(uri):
    """Decides wheter a url looks like a "file" or anything else."""
    if uri.endswith('.gz') or ".tar" in uri or ".zip" in uri:
        return True
    return False


class CacheHandler(web.RequestHandler):
    """Proxy handler for all incoming requests"""

    @web.asynchronous
    def get(self, url):
        """Handle an URL"""

        self.url = url
        print("Request:", url)
        if looks_like_a_file(url):
            filename = os.path.join(getconfig('pkg_cache'), url)
            if os.path.isfile(filename):
                print("File exists, serving it")
                with open(filename, "rb") as f:
                    header = 'attachment; filename="{}"'.format(
                        os.path.basename(url)
                    )
                    self.set_header('Content-Disposition', header)
                    self.set_header('Content-Type', 'application/octet-stream')
                    self.write(f.read())
                    self.finish()
                    return

            # Download and stream it
            gevent.spawn(downloader, self, getconfig('pypi_url') + url, filename)
        else:
            # Just proxy anything back and rewrite returned PyPi urls
            if not os.path.isdir(getconfig('page_cache')):
                os.makedirs(getconfig('page_cache'))

            self.cache_file = os.path.join(
                getconfig('page_cache'),
                md5(url.encode("UTF-8")).hexdigest()
            )
            if os.path.isfile(self.cache_file):
                with open(self.cache_file, "rb") as f:
                    try:
                        cached = pickle.load(f)

                        print("Sending {} from local cache".format(self.url))
                        self.set_header('Content-Type', cached['Content-Type'])
                        self.write(cached['body'])
                        self.finish()
                        return
                    except (EOFError, TypeError, ValueError):
                        # Cache is broken, delete it
                        os.unlink(self.cache_file)

            client = httpclient.AsyncHTTPClient()
            client.fetch(getconfig('pypi_url') + url, self.on_finish_other)

    def on_finish_other(self, response):
        """Handle non-file responses"""
        body = response.body.replace(getconfig('pypi_url'), getconfig('server_url'))
        with open(self.cache_file, "wb") as f:
            pickle.dump({
                'Content-Type': response.headers['Content-Type'],
                'filename': os.path.basename(self.url),
                'body': body,
                'url': self.url,
            }, f)

        self.write(body)
        self.finish()

    def compute_etag(self):
        """Disable generation of etags"""
        return None

def main():
    options.parse_command_line()

    app = web.Application([
        (r'/(.*?)', CacheHandler)
    ])
    app.listen(int(getconfig('server_port')))
    autoreload.start()
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
