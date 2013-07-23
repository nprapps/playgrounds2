#!/usr/bin/env python

import datetime
from glob import glob
import json
import os
import time

import boto.cloudsearch
import boto.ses
from csvkit import CSVKitDictReader
import requests
from peewee import *
import pytz

import app
import app_config
import copytext
from models import Playground, PlaygroundFeature, Revision


def update_search_index(playgrounds):
    if not playgrounds:
        playgrounds = Playground.select()

    print 'Generating SDF batch...'
    sdf = [playground.sdf() for playground in playgrounds]
    payload = json.dumps(sdf)

    if len(payload) > 5000 * 1024:
        print 'Exceeded 5MB limit for SDF uploads!'
        return

    print 'Uploading to CloudSearch...'
    response = requests.post('http://%s/2011-02-01/documents/batch' % app_config.CLOUD_SEARCH_DOC_DOMAIN, data=payload, headers={ 'Content-Type': 'application/json' })

    print response.status_code
    print response.text


def deploy_to_s3(src):
    s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --guess-mime-type --recursive --exclude-from gzip_types.txt sync %s/ %s'
    s3cmd_gzip = 's3cmd -P --add-header=Cache-Control:max-age=5 --add-header=Content-encoding:gzip --guess-mime-type --recursive --exclude "*" --include-from gzip_types.txt sync %s/ %s'

    for bucket in app_config.S3_BUCKETS:
        os.system(s3cmd % (src, 's3://%s/%s/' % (bucket, app_config.PROJECT_SLUG)))
        os.system(s3cmd_gzip % (src, 's3://%s/%s/' % (bucket, app_config.PROJECT_SLUG)))


def gzip(src, dst):
    os.system('python gzip_www.py %s %s' % (src, dst))
    os.system('rm -rf %s/live-data' % dst)


def app_config_js():
    from app import _app_config_js

    response = _app_config_js()
    js = response[0]

    with open('www/js/app_config.js', 'w') as f:
        f.write(js)


def update_copy():
    os.system('curl -o data/copy.xls "%s"' % app_config.COPY_URL)


def less():
    for path in glob('less/*.less'):
        filename = os.path.split(path)[-1]
        name = os.path.splitext(filename)[0]
        out_path = 'www/css/%s.less.css' % name

        os.system('node_modules/.bin/lessc %s %s' % (path, out_path))


def jst():
    os.system('node_modules/.bin/jst --template underscore jst www/js/templates.js')


def render_playgrounds(playgrounds=None):
    """
    Render the playgrounds pages.
    """
    from flask import g, url_for

    update_copy()
    less()
    jst()

    if not playgrounds:
        playgrounds = Playground.select()

    slugs = [p.slug for p in playgrounds]

    app_config_js()
    copy_text_js()

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


def send_revision_email(revision_group):
    payload = app._prepare_email(revision_group)
    addresses = app_config.ADMIN_EMAILS
    send_email(addresses, payload)


def send_email(addresses, payload):
    connection = boto.ses.connect_to_region('us-east-1')
    connection.send_email(
        'NPR News Apps <nprapps@npr.org>',
        'Playgrounds: %s' % (datetime.datetime.now(pytz.utc).replace(tzinfo=pytz.utc).strftime('%m/%d')),
        None,
        addresses,
        html_body=payload,
        format='html')


def load_playgrounds(path='data/playgrounds.csv'):
    """
    Load playground data from the CSV into sqlite.
    """
    features = copytext.COPY.feature_list
    
    with open(path) as f:
        rows = CSVKitDictReader(f)

        for row in rows:
            if row['Duplicate'] == 'TRUE':
                #print 'Skipping duplicate: %s' % row['NAME']
                continue

            playground = Playground.create(
                nprid=row['NPRID'],
                name=row['NAME'],
                facility=row['FACILITY'],
                facility_type=row['FACILITY_TYPE'],
                address=row['ADDRESS'],
                city=row['CITY'],
                state=row['STATE'],
                zip_code=row['ZIP'],
                longitude=float(row['LONGITUDE']) if row['LONGITUDE'] else None,
                latitude=float(row['LATITUDE']) if row['LATITUDE'] else None,
                agency=row['Agency'],
                agency_type=row['AgencyType'],
                owner=row['OWNER'],
                owner_type=row['OWNER_TYPE'],
                remarks=row['REMARKS'],
                public_remarks=row['PubRermarks'],
                url=row['url'],
                entry=row['Entry'],
                source=row['Source']
            )
            
            for feature in features:
                slug = feature['key']

                if row[slug] == 'TRUE':
                    PlaygroundFeature.create(
                        slug=slug,
                        playground=playground
                    )

            Revision.create(
                timestamp=datetime.datetime.now(pytz.utc),
                action='insert',
                playground=playground,
                log=json.dumps([]),
                headers='',
                cookies='',
                revision_group=1
            )

def process_changes(path='changes-in-progress.json'):
    """
    Iterate over changes-in-progress.json and process its contents.
    """
    revision_group = time.mktime((datetime.datetime.now(pytz.utc)).timetuple())

    with open(path) as f:
        changes = json.load(f)

    # A list new or updated playgrounds
    changed_playgrounds = []

    for record in changes:
        if record['action'] == 'update':
            playground, revisions = process_update(record)
            changed_playgrounds.append(playground)
        elif record['action'] == 'insert':
            playground, revisions = process_insert(record)
            changed_playgrounds.append(playground)
        elif record['action'] == 'delete-request':
            playground, revisions = process_delete(record)

        timestamp = datetime.datetime.fromtimestamp(record['timestamp']).replace(tzinfo=pytz.utc)

        Revision.create(
            timestamp=timestamp,
            action=record['action'],
            playground=playground,
            log=json.dumps(revisions),
            headers=json.dumps(record['request']['headers']),
            cookies=json.dumps(record['request']['cookies']),
            revision_group=revision_group
        )

    return (changed_playgrounds, revision_group)


def process_update(record):
    """
    Process a single update record from changes.json.
    """
    playground_id = record['playground']['id']

    # First, capture the old data from this playground.
    old_data = Playground.get(id=playground_id).__dict__['_data']

    # This is an intermediate data store for this record.
    record_dict = {}

    # Loop through each of the key/value pairs in the playground record.
    for key, value in record['playground'].items():

        # Ignore some keys because they aren't really what we want to update.
        if key not in ['id', 'features']:

            # If the value is blank, make it null.
            # Life is too short for many different kinds of emptyness.
            if value == u'':
                value = None

            # Update the record_dict with our new key/value pair.
            record_dict[key] = value

    # Run the update query against this playground.
    # Pushes any updates in the record_dict to the model.
    playground = Playground.get(id=playground_id)

    if (record_dict):
        for k, v in record_dict.items():
            setattr(playground, k, v)
            playground.save()

    # Set up the list of old features.
    # We're going to remove them all.
    # We'll re-add anything that stuck around.
    old_features = []

    # Append the old features to the list.
    for feature in PlaygroundFeature.select().where(PlaygroundFeature.playground == playground_id):
        old_features.append(feature.slug)

    # Delete any features attached to this playground.
    PlaygroundFeature.delete().where(PlaygroundFeature.playground == playground_id).execute()

    # Check to see if we have any incoming features.
    try:
        features = record['playground']['features']
    except KeyError:
        features = []

    for slug in features:
        PlaygroundFeature.create(
            slug=slug,
            playground=playground
        )

    # Now, let's set up some revisions.
    # Create a list of revisions to apply.
    revisions = []

    # Our old data was captured up top. It's called old_data.
    # This is the new data. It's just the record_dict from above.
    new_data = record_dict

    # Loop over the key/value pairs in the new data we have.
    for key, value in new_data.items():

        # Fix the variety of None that we bother maintaining.
        if value is None:
            new_data[key] = ''

        # Now, if the old data and the new data don't match, let's make a revision.
        if old_data[key] != new_data[key]:

            # Set up an intermediate data structure for the revision.
            revision_dict = {}

            # Set up the data for this revision.
            revision_dict['field'] = key
            revision_dict['from'] = old_data[key]
            revision_dict['to'] = new_data[key]

            # Append it to the revisions list.
            revisions.append(revision_dict)

    # Let's get started on features.
    # First, let's figure out the new features coming from the Web.
    try:
        # If there are any new features, create a list for them.
        new_features = record['playground']['features']
    except:
        # Otherwise, empty list.
        new_features = []

    # First case: If the list of old and new features is identical, don't do anything.
    if old_features != new_features:
        # So there's a difference between the old and new feature lists.
        # Since the Web can both add new features and remove old features,
        # we have to prepare for each path.
        # First, let's loop over the list of features that are available.
        for feature in copytext.COPY.feature_list:
            slug = feature['key']

            # If the slug is in the old feature set, let's check it against the new.
            if slug in old_features:

                # If it's not in the new feature set but IS in the old feature set,
                # let's append a revision taking it from 1 to 0.
                if slug not in new_features:
                    revisions.append({"field": slug, "from": 1, "to": 0})

            # Similarly, if the slug in the new feature set, let's check it agains the old.
            if slug in new_features:

                # If it's not in the old_feature set but IS in the new feature set,
                # let's append a revision taking it from 0 to 1.
                if slug not in old_features:
                    revisions.append({"field": slug, "from": 0, "to": 1})

    return playground, revisions

def process_insert(record):
    """
    Process a single insert record from changes.json.
    """
    playground = Playground()

    record_dict = {}

    # Loop through each of the key/value pairs in the playground record.
    for key, value in record['playground'].items():

        # Ignore some keys because they aren't really what we want to update.
        if key not in ['id', 'features']:

            # If the value is blank, make it null.
            # Life is too short for many different kinds of emptyness.
            if value == u'':
                value = None

            # Update the record_dict with our new key/value pair.
            record_dict[key] = value
            setattr(playground, key, value)

    playground.save()

    # Create a list of revisions that were applied.
    revisions = []

    # Our old data was captured up top. It's called old_data.
    # This is the new data. It's just the record_dict from above.
    new_data = record_dict

    # Loop over the key/value pairs in the new data we have.
    for key, value in new_data.items():

        # Fix the variety of None that we bother maintaining.
        if value is None:
            new_data[key] = ''

        # Set up an intermediate data structure for the revision.
        revision_dict = {}

        # Set up the data for this revision.
        revision_dict['field'] = key
        revision_dict['from'] = ''
        revision_dict['to'] = new_data[key]

        # Append it to the revisions list.
        revisions.append(revision_dict)

    # Check to see if we have any incoming features.
    try:
        features = record['playground']['features']
    except KeyError:
        features = []

    for feature in features:
        PlaygroundFeature.create(
            slug=slug,
            playground=playground
        )

        revisions.append({'field': slug, 'from': 0, 'to': 1})

    return (playground, revisions)

def process_delete(record):
    """
    Create a revision from the delete requests.
    """
    playground_slug = record['playground']['slug']

    playground = Playground.get(slug=playground_slug)

    revisions = [{"field": "active", "from": True, "to": False}, {"field": "reason", "from": "", "to": record['playground']['text']}]

    return (playground, revisions)

def render_sitemap():
    with app.app.test_request_context(path='sitemap.xml'):
        content = app.sitemap()

        if isinstance(content, tuple):
            content = content[0]

    with open('www/sitemap.xml', 'w') as f:
        f.write(content.encode('utf-8'))

