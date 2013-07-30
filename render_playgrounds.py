#!/usr/bin/env python

import os

import app
import app_config
import copytext

from models import get_active_playgrounds


def render_playgrounds(playgrounds=None):
    """
    Render the playgrounds pages.
    """
    from flask import g, url_for
    from app import _app_config_js

    os.system('curl -o data/copy.xls "%s"' % app_config.COPY_URL)
    for path in glob('less/*.less'):
        filename = os.path.split(path)[-1]
        name = os.path.splitext(filename)[0]
        out_path = 'www/css/%s.less.css' % name

        os.system('node_modules/.bin/lessc %s %s' % (path, out_path))

    os.system('node_modules/.bin/jst --template underscore jst www/js/templates.js')

    if not playgrounds:
        playgrounds = get_active_playgrounds()

    slugs = [p.slug for p in playgrounds]

    response = _app_config_js()
    js = response[0]

    with open('www/js/app_config.js', 'w') as f:
        f.write(js)

    compiled_includes = []

    updated_paths = []

    for slug in slugs:
        # Silly fix because url_for require a context
        with app.app.test_request_context():
            path = url_for('_playground', playground_slug=slug)

        with app.app.test_request_context(path=path):
            print 'Rendering %s' % path

            g.compile_includes = True
            g.compiled_includes = compiled_includes

            view = app.__dict__['_playground']
            content = view(slug)

            compiled_includes = g.compiled_includes

        path = '.playgrounds_html%s' % path

        # Ensure path exists
        head = os.path.split(path)[0]

        try:
            os.makedirs(head)
        except OSError:
            pass

        with open(path, 'w') as f:
            f.write(content.encode('utf-8'))

        updated_paths.append(path)

    return updated_paths


if __name__ == '__main__':
    render_playgrounds()
