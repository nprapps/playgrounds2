#!/usr/bin/env python

import datetime
import json
import os
import time

from flask import Flask, redirect

import app_config
import data

app = Flask(app_config.PROJECT_NAME)


def write_data(payload, write_mode):
    """
    DRYs out the process of editing/creating the updates.json file.
    It sucks that there is no single mode for read/edit/create a file.
    """
    with open('data/updates.json', write_mode) as f:

        if write_mode == 'r+':
            # If the mode is r+, read the file into a list before doing other things.
            # Get the file data.
            filedata = f.read()

            # Seek to the beginning of the file.
            f.seek(0)

            # Load the file -- it's a list.
            output = json.loads(filedata)

            # Nuke the file contents.
            f.truncate()

        else:
            # If the mode is w, set up a blank list, since the file doesn't exist.
            output = []

        # Append our payload to the list we have created.
        output.append(payload)

        # Write the output to the file.
        f.write(json.dumps(output))


@app.route('/%s/' % app_config.PROJECT_SLUG)
def _dynamic_page():
    """
    Example dynamic view demonstrating rendering a simple HTML page.
    """
    return datetime.datetime.now().isoformat()


@app.route('/%s/edit-playground/' % app_config.PROJECT_SLUG, methods=['POST'])
def edit_playground():

    # Get the current state of the request global.
    from flask import request

    # Only handle POST requests.
    if request.method == 'POST':

        # How to know what fields are on this model?
        # Pick a single instance from the DB and serialize it.
        playground = data.Playground.get(id=request.form.get('id'))
        playground_fields = playground.__dict__['_data'].keys()

        # Prep the payload.
        payload = {}
        payload['playground'] = {}
        payload['request'] = {}
        payload['request']['headers'] = {}

        # Write the request headers to the payload.
        # It's nicer when they use underscores instead of dashes.
        for key, value in request.headers:
            payload['request']['headers'][key.lower().replace('-', '_')] = value

        # Write the request cookies to the payload.
        payload['request']['cookies'] = request.cookies

        # Loop over all of the model fields looking to see if they're present in the POST.
        for field in playground_fields:

            # Transform integers into ints when possible.
            try:
                payload['playground'][field] = int(request.form.get(field, None))
            except ValueError:
                payload['playground'][field] = request.form.get(field, None)
            except TypeError:
                pass

            # If there are weird blanks, make them appropriate Python nulls.
            # Sucks when there are like three different kinds of "blank."
            try:
                if payload['playground'][field] in ['', 'None']:
                    payload['playground'][field] = None
            except KeyError:
                pass

        # Special-case handling for zip_code, which is a string, not an int.
        try:
            payload['playground']['zip_code'] = str(payload['playground']['zip_code'])
        except KeyError:
            pass

        # Append a timestamp.
        payload['playground']['timestamp'] = time.mktime((datetime.datetime.utcnow()).timetuple())

        # Set up a list for features.
        payload['playground']['features'] = []

        # Loop over all of the possible features to see if they're present in the POST.
        for f, slug in app_config.FEATURE_LIST:
            if request.form.get(slug, None):
                payload['playground']['features'].append(slug)

        # If there weren't any features in this POST, remove the features list from payload.
        if len(payload['playground']['features']) == 0:
            del(payload['playground']['features'])

        # Write to the updates.json file.
        if os.path.exists("data/updates.json"):
            # If the file already exists, load it as r+ so we can read AND write it.
            write_data(payload, 'r+')
        else:
            # If the file doesn't exist, load it as w so that we can create it.
            # Can you believe r+ won't create a file? That's turrible.
            write_data(payload, 'w')

        return redirect('%s/playground/%s.html?action=editing_thanks' % (app_config.S3_BASE_URL, playground.slug))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=app_config.DEBUG)
