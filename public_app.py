#!/usr/bin/env python

import datetime
import json
import os
import time

from flask import Flask

import app_config
import data

app = Flask(app_config.PROJECT_NAME)


@app.route('/%s/' % app_config.PROJECT_SLUG)
def _dynamic_page():
    """
    Example dynamic view demonstrating rendering a simple HTML page.
    """
    return datetime.datetime.now().isoformat()


@app.route('/%s/api/' % app_config.PROJECT_SLUG, methods=['POST'])
def _api():

    def write_data(payload, write_mode):
        with open('data/updates.json', write_mode) as f:

            if write_mode == 'r+':
                filedata = f.read()
                f.seek(0)
                output = json.loads(filedata)
                f.truncate()
            else:
                output = []

            output.append(payload)
            f.write(json.dumps(output))

    from flask import request

    if request.method == 'POST':

        p = data.Playground.select()[0]
        payload = {}
        payload['playground'] = {}
        payload['request'] = {}
        payload['request']['headers'] = {}

        for key, value in request.headers:
            payload['request']['headers'][key.lower().replace('-', '_')] = value

        payload['request']['cookies'] = request.cookies

        for field in p.__dict__['_data'].keys():

            try:
                payload['playground'][field] = int(request.form.get(field, None))
            except ValueError:
                payload['playground'][field] = request.form.get(field, None)
            except TypeError:
                pass

            try:
                if payload['playground'][field] in ['', 'None']:
                    payload['playground'][field] = None
            except KeyError:
                pass

        payload['playground']['zip_code'] = str(payload['playground']['zip_code'])

        payload['playground']['timestamp'] = time.mktime((datetime.datetime.utcnow()).timetuple())

        payload['playground']['features'] = []

        print request.form

        for f, slug in app_config.FEATURE_LIST:
            if request.form.get(slug, None):
                payload['playground']['features'].append(slug)

        if os.path.exists("data/updates.json"):
            write_data(payload, 'r+')
        else:
            write_data(payload, 'w')

        return json.dumps(payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=app_config.DEBUG)
