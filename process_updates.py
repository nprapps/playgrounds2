#!/usr/bin/env python

import datetime
import os
import time

from jinja2 import Template

import app_config
import data
import pytz


def process_updates(path=None, local=None):
    now_datetime = datetime.datetime.now(pytz.utc)
    now = time.mktime(now_datetime.timetuple())

    changes = 0

    if not path:
        path = '/home/ubuntu/apps/%s/repository/' % app_config.PROJECT_SLUG

    if os.path.exists('%sdata/changes.json' % path):

        os.system('rm -rf %s.playgrounds_html/' % path)
        os.system('rm -rf %s.playgrounds_gzip/' % path)
        os.system('cp %splaygrounds.db data/%s-playgrounds.db' % (path, now))
        os.system('cp %sdata/changes.json data/%s-changes.json' % (path, now))
        os.system('mv %sdata/changes.json %schanges-in-progress.json' % (path, path))

        # Create our list of changed items and a revision group.
        changed_playgrounds, revision_group = data.process_changes()

        # Render and deploy.
        data.render_playgrounds(changed_playgrounds)
        data.render_sitemap()

        if not local or local is False:
            data.gzip('%s.playgrounds_html' % path, '%s.playgrounds_gzip' % path)
            data.deploy_to_s3('%s.playgrounds_gzip' % path)

            data.gzip('www/sitemap.xml', 'gzip/sitemap.xml')
            data.deploy_file_to_s3('gzip/sitemap.xml')

            # Update the search index.
            data.update_search_index(changed_playgrounds)

        # Send the revision email.
        data.send_revision_email(revision_group)

        # Remove files and old state.
        os.system('rm -f %schanges-in-progress.json' % path)
        os.system('rm -rf %s.playgrounds_html/' % path)
        os.system('rm -rf %s.playgrounds_gzip/' % path)

        # Show changes.
        changes = len(changed_playgrounds)

    else:
        context = {}
        context['total_revisions'] = 0
        context['deletes'] = {}
        context['deletes']['playgrounds'] = []
        context['deletes']['total_revisions'] = 0
        context['inserts'] = {}
        context['inserts']['playgrounds'] = []
        context['inserts']['total_revisions'] = 0
        context['updates'] = {}
        context['updates']['playgrounds'] = []
        context['updates']['total_revisions'] = 0

        with open('%stemplates/_email.html' % path, 'rb') as read_template:
            payload = Template(read_template.read())

        payload = payload.render(**context)
        addresses = app_config.ADMIN_EMAILS
        data.send_email(addresses, payload)

    print '%s changes | %s' % (changes, now_datetime.isoformat())

if __name__ == '__main__':
    process_updates(path=None, local=False)
