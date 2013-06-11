#!/usr/bin/env python

import datetime
import json
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
    from flask import request

    if request.method == 'POST':

            p = data.Playground.select()[0]
            payload = {}

            for field in p.__dict__['_data'].keys():

                try:
                    payload[field] = int(request.form.get(field, None))
                except ValueError:
                    payload[field] = request.form.get(field, None)

                if payload[field] in ['', 'None']:
                    payload[field] = None

            payload['timestamp'] = time.mktime((datetime.datetime.utcnow()).timetuple())
            return json.dumps(payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=app_config.DEBUG)
