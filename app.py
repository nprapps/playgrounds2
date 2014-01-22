#!/usr/bin/env python

import cgi
from datetime import date
import datetime
import json
from mimetypes import guess_type
import re
from sets import Set
import urllib

import envoy
from flask import Flask, Markup, abort, render_template, url_for
from jinja2 import Template
import requests

import app_config
import copytext
from models import Playground, Revision, display_field_name, get_active_playgrounds
from render_utils import flatten_app_config, make_context

import argparse

app = Flask(app_config.PROJECT_NAME)


@app.route('/email/<revision_group>/')
def _prepare_email(revision_group):
    revisions = Revision.select().where(Revision.revision_group == int(revision_group))

    context = {}
    context['base_url'] = '%s/playground/' % app_config.S3_BASE_URL
    context['total_revisions'] = revisions.count()
    context['deletes'] = {}
    context['deletes']['playgrounds'] = []
    context['deletes']['total_revisions'] = 0

    context['inserts'] = {}
    context['inserts']['playgrounds'] = []
    context['inserts']['total_revisions'] = 0

    context['updates'] = {}
    context['updates']['playgrounds'] = []
    context['updates']['total_revisions'] = 0

    inserts = revisions.where(Revision.action == 'insert')
    if inserts.count() > 0:
        context['inserts']['total_revisions'] = inserts.count()
        for revision in inserts:
            p = Playground.get(slug=revision.playground.slug)
            playground_dict = p.__dict__['_data']
            playground_dict['display_name'] = p.display_name
            playground_dict['site_url'] = '%s/playground/%s.html' % (app_config.S3_BASE_URL, revision.playground.slug)
            playground_dict['revision_group'] = int(revision_group)
            playground_dict['headers'] = revision.get_headers()
            playground_dict['feature_count'] = int(p.feature_count)
            nearby = p.nearby(3)
            playground_dict['nearby'] = []
            for n in nearby:
                if n.distance < 0.5:
                    playground_dict['nearby'].append(n)
            context['inserts']['playgrounds'].append(playground_dict)
        context['inserts']['playgrounds'] = sorted(context['inserts']['playgrounds'], key=lambda p: p['name'])

    deletes = revisions.where(Revision.action == 'delete-request')
    if deletes.count() > 0:
        context['deletes']['total_revisions'] = deletes.count()
        for revision in deletes:
            p = Playground.get(slug=revision.playground.slug)
            playground_dict = playground_dict = p.__dict__['_data']
            playground_dict['display_name'] = p.display_name
            playground_dict['site_url'] = '%s/playground/%s.html' % (app_config.S3_BASE_URL, revision.playground.slug)
            playground_dict['delete_url'] = '%s/delete-playground/%s/' % (app_config.SERVER_BASE_URL, revision.playground.slug)
            playground_dict['revision_group'] = int(revision_group)
            for item in json.loads(revision.log):
                if item.get('field', None) == "reason":
                    playground_dict['text'] = cgi.escape(item.get('to'))
            playground_dict['headers'] = revision.get_headers()
            context['deletes']['playgrounds'].append(playground_dict)
        context['deletes']['playgrounds'] = sorted(context['deletes']['playgrounds'], key=lambda p: p['name'])

    updates = revisions.where(Revision.action == 'update')
    if updates.count() > 0:
        context['updates']['total_revisions'] = updates.count()
        updated_playgrounds = Set([])

        for revision in updates:
            updated_playgrounds.add(revision.playground.slug)

        for playground_slug in updated_playgrounds:
            p = Playground.get(slug=playground_slug)
            playground_dict = p.__dict__['_data']
            playground_dict['display_name'] = p.display_name
            playground_dict['site_url'] = '%s/playground/%s.html' % (app_config.S3_BASE_URL, playground_slug)
            playground_dict['revisions'] = []
            for revision in updates:
                if revision.playground.id == p.id:
                    revision_dict = {}
                    revision_dict['revision_group'] = revision_group
                    revision_dict['fields'] = revision.get_log()
                    revision_dict['headers'] = revision.get_headers()
                    playground_dict['revisions'].append(revision_dict)

            context['updates']['playgrounds'].append(playground_dict)
        context['updates']['playgrounds'] = sorted(context['updates']['playgrounds'], key=lambda p: p['name'])

    with open('templates/_email.html', 'rb') as read_template:
        payload = Template(read_template.read())

    return payload.render(**context)


@app.route('/email/')
def _list_revision_groups():

    context = {}
    context['revision_groups'] = Set([])

    revisions = Revision.select()

    for revision in revisions:
        revision_date = datetime.datetime.fromtimestamp(revision.revision_group)
        context['revision_groups'].add((revision_date, revision.revision_group))

    context['revision_groups'] = sorted(context['revision_groups'], key=lambda g: g[0], reverse=True)

    return render_template('_email_list.html', **context)


def intcomma(value):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    value = str(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', value)
    if value == new:
        return new
    else:
        return intcomma(new)

@app.route('/')
def index():
    """
    Playgrounds index page.
    """
    context = make_context()
    metros = app_config.METRO_AREAS

    for metro in metros:
        metro['playground_count'] = Playground.select().where(Playground.zip_code << metro['zip_codes']).count()

    context['playground_count'] = intcomma(Playground.select().count())

    context['metros'] = metros

    return render_template('index.html', **context)

@app.route('/search.html')
def search():
    """
    Search results page.
    """
    context = make_context()

    return render_template('search.html', **context)

@app.route('/create.html')
def playground_create():
    context = make_context()
    context['features'] = Playground.features_form()

    return render_template('create.html', **context)

@app.route('/sitemap.xml')
def sitemap():
    """
    Renders a sitemap.
    """
    context = make_context()
    context['pages'] = []

    now = date.today().isoformat()

    context['pages'].append(('/', now))

    for playground in get_active_playgrounds():
        context['pages'].append((url_for('_playground', playground_slug=playground.slug), now))

    sitemap = render_template('sitemap.xml', **context)

    return (sitemap, 200, { 'content-type': 'application/xml' })

@app.route('/widget.html')
def widget():
    """
    Embeddable widget example page.
    """
    return render_template('widget.html', **make_context())

@app.route('/test_widget.html')
def test_widget():
    """
    Example page displaying widget at different embed sizes.
    """
    return render_template('test_widget.html', **make_context())

@app.route('/js/embed-widget.js')
def embed_widget():
    """
    Javascript to embed the widget
    """
    return render_template('embed_widget.js', **make_context())

@app.route('/playground/<string:playground_slug>.html')
def _playground(playground_slug):
    """
    Playground detail page.
    """
    from flask import request
    context = make_context()

    context['playground'] = Playground.get(slug=playground_slug)
    context['fields'] = context['playground'].update_form()
    context['features'] = context['playground'].update_features_form()
    context['revisions'] = Revision.select()\
                            .where(Revision.playground == context['playground'].id)\
                            .where((Revision.action == 'insert') | (Revision.action == 'update'))\
                            .order_by(Revision.timestamp.desc())
    context['display_field_name'] = display_field_name
    context['path'] = request.path

    return render_template('playground.html', **context)

@app.route('/cloudsearch/<path:path>')
def _cloudsearch_proxy(path):
    from flask import request

    args = {}

    # Convert immutable MultiDict to dict
    for k, v in request.args.items():
        args[k] = v[0] if isinstance(v, list) else v

    if 'callback' in request.args:
        callback = request.args['callback']
        del args['callback']
    else:
        callback = None

    url = 'http://%s/%s?%s' % (app_config.CLOUD_SEARCH_DOMAIN, path, urllib.urlencode(args))

    response = requests.get(url)

    if response.status_code == 507:
        return ('%s({ "error": "507" });' % callback, 200, response.headers);

    output = response.text

    if callback:
        output = '%s(%s);' % (callback, output)

    return (output, response.status_code, response.headers)

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

    r = envoy.run('node_modules/bin/lessc -', data=less)

    return r.std_out, 200, { 'Content-Type': 'text/css' }

# Render JST templates on-demand
@app.route('/js/templates.js')
def _templates_js():
    r = envoy.run('node_modules/bin/jst --template underscore jst')

    return r.std_out, 200, { 'Content-Type': 'application/javascript' }

# Render application configuration
@app.route('/js/app_config.js')
def _app_config_js():
    """
    This includes both client-side config and some COPY vars we need in JS.
    """
    config = flatten_app_config()
    js = 'window.APP_CONFIG = ' + json.dumps(config) + ';'

    features = {}

    for feature in copytext.COPY.feature_list:
        features[feature['key']] = feature._row

    features = 'window.FEATURES = ' + json.dumps(features) + ';'

    return '\n'.join([js, features]), 200, { 'Content-Type': 'application/javascript' }

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
