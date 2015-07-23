#!/usr/bin/env python

import datetime
import json
import os
import time

from flask import Flask, redirect, abort
import pytz

import app_config
import copytext
from models import Playground

app = Flask(app_config.PROJECT_NAME)

def write_data(payload, path='data/changes.json'):
    """
    Write changes.json, maintaining any changes already written.
    """
    # If file exists, read its contents then clear it
    if os.path.exists(path):
        f = open(path, 'r+')
        filedata = f.read()

        f.seek(0)

        try:
            output = json.loads(filedata)
        except ValueError:
            output = []

        f.truncate()
    # Otherwise just open file for writing
    else:
        f = open(path, 'w')

        output = []

    # Add new changes to any existing changes
    output.append(payload)

    f.write(json.dumps(output, indent=4))
    f.close()

@app.route('/%s/test/' % app_config.PROJECT_SLUG, methods=['GET'])
def _test_app():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


@app.route('/%s/' % app_config.PROJECT_SLUG)
def _dynamic_page():
    """
    Example dynamic view demonstrating rendering a simple HTML page.
    """
    return datetime.datetime.now().isoformat()


def create_change_payload(action, request):
    """
    Create a changes.json entry.
    """
    payload = {}
    payload['action'] = action
    payload['timestamp'] = time.mktime(datetime.datetime.now(pytz.utc).timetuple())
    payload['playground'] = {}
    payload['request'] = {}
    payload['request']['ip_address'] = request.remote_addr
    payload['request']['cookies'] = request.cookies
    payload['request']['headers'] = {}

    # Write the request headers to the payload.
    # It's nicer when they use underscores instead of dashes.
    for key, value in request.headers:
        payload['request']['headers'][key.lower().replace('-', '_')] = value

    if action != 'delete-request':
        # Process playground fields
        for field in Playground.USER_EDITABLE_FIELDS:
            val = request.form.get(field)

            if field == 'reverse_geocoded':
                payload['playground'][field] = (val == 'on')  
            elif val:
                op = Playground.FIELD_OPS[getattr(Playground, field).__class__]
                payload['playground'][field] = op(val)
            else:
                if field in ['latitude', 'longitude']:
                    payload['playground'][field] = None
                else:
                    payload['playground'][field] = ''

        payload['playground']['features'] = []

        # Process playground features
        #for feature in copytext.Copy(app_config.COPY_PATH)['feature_list']:
            #slug = feature['key']

            #if request.form.get(slug, None):
                #payload['playground']['features'].append(slug)

    return payload


@app.route('/%s/insert-playground/' % app_config.PROJECT_SLUG, methods=['POST'])
def insert_playground():
    """
    Create a new playground with data cross-posted from the app.
    """
    from flask import request

    if request.method != 'POST':
        abort(401)

    payload = create_change_payload('insert', request)

    write_data(payload)

    return redirect('%s/search.html?action=create_thanks' % (app_config.S3_BASE_URL))


@app.route('/%s/update-playground/' % app_config.PROJECT_SLUG, methods=['POST'])
def update_playground():
    """
    Update a single playground.
    """
    from flask import request

    if request.method != 'POST':
        abort(401)

    playground = Playground.get(id=request.form.get('id'))

    payload = create_change_payload('update', request) 
    payload['playground']['id'] = int(request.form.get('id'))

    write_data(payload)

    return redirect('%s/playground/%s.html?action=editing_thanks' % (app_config.S3_BASE_URL, playground.slug))


@app.route('/%s/request-delete-playground/' % app_config.PROJECT_SLUG, methods=['POST'])
def delete_playground():
    """
    Recommend a playground for deletion.
    """
    from flask import request

    playground_slug = request.form.get('slug', None)
    text = request.form.get('text', '')

    if not playground_slug:
        abort(400)

    payload = create_change_payload('delete-request', request)

    payload['playground']['slug'] = playground_slug
    payload['playground']['text'] = text

    write_data(payload)

    return redirect('%s/playground/%s.html?action=deleting_thanks' % (app_config.S3_BASE_URL, playground_slug))


@app.route('/%s/delete-playground/<playground_slug>/' % app_config.PROJECT_SLUG, methods=['GET'])
def delete_playground_confirm(playground_slug=None):
    """
    Confirm deleting a playground.
    """
    from flask import request

    if request.method != 'GET':
        abort(401)

    if not playground_slug:
        abort(400)

    Playground.get(slug=playground_slug).deactivate()

    return json.dumps({
        'slug': playground_slug,
        'action': 'delete',
        'success': True
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=app_config.DEBUG)
