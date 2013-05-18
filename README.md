pip-proxy
=========

A simple caching proxy server for pip. Proxies and rewrites any requests
to PyPi and caches them. It never redirects clients to PyPi like other
solutions, so your pip clients don't need a direct internet connection.

It's currently in beta and not really stable. Don't blindly rely on it!

Why should I use it?
--------------------

- PyPi is kinda slow and sometimes even completely down
- Create virtualenvs with all your needed packages within seconds

Quickstart
----------

1. Install development headers

        sudo apt-get install python-dev libevent-dev

2. Create a virtualenv

        virtualenv mypip
        cd mypip
        . bin/activate
 
3. Clone this repository

        git clone https://github.com/DerMitch/pip-proxy.git
        cd pip-proxy
        pip install -r requirements.txt

4. Edit configuration (config.ini)

5. Run!

        python pip-proxy.py

6. Use it with pip

        pip install -U --index-url=http://localhost:8080/simple/ --timeout=600 django sqlalchemy redis

7. Add to your ~/.pip/pip.conf

        [global]
        timeout = 600
        index-url = http://server:8080/simple/
