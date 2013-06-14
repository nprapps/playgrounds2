#!/usr/bin/env python

from datetime import date
import json
from mimetypes import guess_type
import urllib

import envoy
from flask import Flask, Markup, abort, render_template, url_for
import requests

import app_config
import data
from render_utils import flatten_app_config, make_context

import argparse

app = Flask(app_config.PROJECT_NAME)


@app.route('/')
def index():
    """
    Playgrounds index page.
    """
    context = make_context()
    context['playgrounds'] = data.Playground.select().limit(10)

    return render_template('index.html', **context)

@app.route('/sitemap.xml')
def sitemap():
    """
    Renders a sitemap.
    """
    context = make_context()
    context['pages'] = []

    now = date.today().isoformat()

    context['pages'].append(('/', now))

    for playground in data.Playground.select():
        context['pages'].append((url_for('_playground', playground_id=playground.id), now))

    sitemap = render_template('sitemap.xml', **context)

    return (sitemap, 200, { 'content-type': 'application/xml' })

@app.route('/playground/<int:playground_id>.html')
def _playground(playground_id):
    """
    Playground detail page.
    """
    context = make_context()
    context['playground'] = data.Playground.get(id=playground_id)
    context['fields'] = context['playground'].update_form()
    context['features'] = context['playground'].feature_form()

    return render_template('playground.html', **context)

@app.route('/playground/create/')
def _playground_create():
    p = data.Playground().select()[0]
    context = make_context()
    context['fields'] = p.create_form()
    context['features'] = p.feature_form()

    return render_template('create.html', **context)

@app.route('/cloudsearch/<path:path>')
def _cloudsearch_proxy(path):
    from flask import request

    url = 'http://%s/%s?%s' % (app_config.CLOUD_SEARCH_DOMAIN, path, urllib.urlencode(request.args))

    response = requests.get(url)

    return (response.text, response.status_code, response.headers)

@app.route('/test/test.html')
def test_dir():
    return render_template('index.html', **make_context())

# Render LESS files on-demand
@app.route('/less/<string:filename>')
def _less(filename):
    try:
        with open('less/%s' % filename) as f:
            less = f.read()
    except IOError:
        abort(404)

    r = envoy.run('node_modules/.bin/lessc -', data=less)

    return r.std_out, 200, { 'Content-Type': 'text/css' }

# Render JST templates on-demand
@app.route('/js/templates.js')
def _templates_js():
    r = envoy.run('node_modules/.bin/jst --template underscore jst')

    return r.std_out, 200, { 'Content-Type': 'application/javascript' }

# Render application configuration
@app.route('/js/app_config.js')
def _app_config_js():
    config = flatten_app_config()
    js = 'window.APP_CONFIG = ' + json.dumps(config)

    return js, 200, { 'Content-Type': 'application/javascript' }

# Server arbitrary static files on-demand
@app.route('/<path:path>')
def _static(path):
    try:
        with open('www/%s' % path) as f:
            return f.read(), 200, { 'Content-Type': guess_type(path)[0] }
    except IOError:
        abort(404)

@app.template_filter('urlencode')
def urlencode_filter(s):
    """
    Filter to urlencode strings.
    """
    if type(s) == 'Markup':
        s = s.unescape()

    s = s.encode('utf8')
    s = urllib.quote_plus(s)

    return Markup(s)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port')
    args = parser.parse_args()
    server_port = 8000
    if args.port:
        server_port = int(args.port)
    app.run(host='0.0.0.0', port=server_port, debug=app_config.DEBUG)
