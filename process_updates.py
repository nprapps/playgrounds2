#!/usr/bin/env python

import datetime
import os
import time

from jinja2 import Template

import app_config
import data
import pytz


def main():
    now = datetime.datetime.now(pytz.utc)
    now = time.mktime(now.timetuple())

    path = '/home/ubuntu/apps/%s/repository' % app_config.PROJECT_SLUG

    if os.path.exists('%s/data/changes.json' % path):

        os.system('rm -rf %s/.playgrounds_html' % path)
        os.system('rm -rf %s/.playgrounds_gzip' % path)
        os.system('cp %s/playgrounds.db data/%s-playgrounds.db' % path, now)
        os.system('cp %s/data/changes.json data/%s-changes.json' % path, now)
        os.system('mv %s/data/changes.json changes-in-progress.json' % path)

        # Create our list of changed items and a revision group.
        changed_playgrounds, revision_group = data.process_changes()

        # Render and deploy.
        data.render_playgrounds(changed_playgrounds)
        data.gzip('%s/.playgrounds_html' % path, '%s/.playgrounds_gzip' % path)
        data.deploy_to_s3('%s/.playgrounds_gzip' % path)

        # Update the search index.
        data.update_search_index(changed_playgrounds)

        # Send the revision email.
        data.send_revision_email(revision_group)

        # Remove files and old state.
        os.system('rm -f %s/changes-in-progress.json' % path)
        os.system('rm -rf %s/.playgrounds_html' % path)
        os.system('rm -rf %s/.playgrounds_gzip' % path)

    else:
        print "No updates to process."
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

        with open('%s/templates/_email.html' % path, 'rb') as read_template:
            payload = Template(read_template.read())

        payload = payload.render(**context)
        addresses = app_config.ADMIN_EMAILS
        data.send_email(addresses, payload)

if __name__ == '__main__':
    main()
