#!/usr/bin/env python

from collections import defaultdict
import copy
import csv
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
from models import Playground, PlaygroundFeature, Revision, database, get_active_playgrounds


def load_from_google_spreadsheet(key):
    r = requests.get("https://docs.google.com/spreadsheet/pub?hl=en&hl=en&key=%s&output=csv" % (key))
    with open('data/gdoc-%s.csv' % (key), 'wb') as writefile:
        writefile.write(r.content)

    with open('data/gdoc-%s.csv' % (key), 'rb') as readfile:
        csvfile = list(csv.DictReader(readfile))

    for row in csvfile:
        payload = dict(row)
        for feature in payload['features'].split(','):
            feature_name = feature.strip().lower().replace(' ', '-')
            payload[feature_name] = 'on'

        payload.pop('features')

        p = requests.post('http://54.214.20.225/playgrounds/insert-playground/', data=payload)
        print p.status_code

def write_data_csv(playgrounds=None):
    """
    Outputs a CSV-ified version of our playgrounds DB.
    """
    if not playgrounds:
        playgrounds = get_active_playgrounds()

    fields = get_active_playgrounds()[0].__dict__['_data'].keys()
    fields.extend([f['key'] for f in copytext.COPY.feature_list])

    with open('www/npr-accessible-playgrounds.csv', 'wb') as csvfile:
        csvwriter = csv.DictWriter(csvfile, fields)
        csvwriter.writeheader()

        for playground in get_active_playgrounds():
            playground_dict = playground.to_dict()
            playground_dict.pop('features')

            for feature in copytext.COPY.feature_list:
                playground_dict[feature['key']] = False

            if playground.features:
                for f in playground.features:
                    playground_dict[f.slug] = True

            csvwriter.writerow(playground_dict)


def write_data_json(playgrounds=None):
    """
    Output a JSON-ified version of our playgrounds DB.
    """
    if not playgrounds:
        playgrounds = get_active_playgrounds()

    payload = {}
    payload['meta'] = {}
    payload['playgrounds'] = []

    payload['meta']['count'] = playgrounds.count()
    payload['meta']['states'] = defaultdict(int)
    payload['meta']['features'] = defaultdict(int)

    for playground in playgrounds:
        payload['meta']['states'][playground.state] += 1

        if playground.features:
            for feature in playground.features:
                payload['meta']['features'][feature.slug.replace('-', ' ')] += 1

        payload['playgrounds'].append(playground.to_dict())

    with open('www/npr-accessible-playgrounds.json', 'wb') as jsonfile:
        jsonfile.write(json.dumps(payload))


def update_search_index(playgrounds):
    if not playgrounds:
        playgrounds = get_active_playgrounds()

    print 'Generating SDF batch...'
    sdf = [playground.sdf() for playground in playgrounds]
    payload = json.dumps(sdf)

    if len(payload) > 5000 * 1024:
        print 'Exceeded 5MB limit for SDF uploads!'
        return

    print 'Uploading to CloudSearch...'
    response = requests.post('http://%s/2011-02-01/documents/batch' % app_config.CLOUD_SEARCH_DOC_DOMAIN, data=payload, headers={'Content-Type': 'application/json'})

    print response.status_code
    print response.text


def deploy_to_s3(src):
    s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --guess-mime-type --recursive --exclude-from gzip_types.txt sync %s/ %s'
    s3cmd_gzip = 's3cmd -P --add-header=Cache-Control:max-age=5 --add-header=Content-encoding:gzip --guess-mime-type --recursive --exclude "*" --include-from gzip_types.txt sync %s/ %s'

    for bucket in app_config.S3_BUCKETS:
        os.system(s3cmd % (src, 's3://%s/' % (bucket)))
        os.system(s3cmd_gzip % (src, 's3://%s/' % (bucket)))


def deploy_file_to_s3(src, dst, gzipped=False):
    if gzipped:
        s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --add-header=Content-encoding:gzip --guess-mime-type --recursive --exclude "*" --include-from gzip_types.txt put %s %s'
    else:
        s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --guess-mime-type --recursive --exclude-from gzip_types.txt put %s %s'

    for bucket in app_config.S3_BUCKETS:
        os.system(s3cmd % (src, 's3://%s/%s' % (bucket, dst)))


def gzip(src, dst):
    os.system('python gzip_www.py %s %s' % (src, dst))


def app_config_js():
    from app import _app_config_js

    response = _app_config_js()
    js = response[0]

    with open('www/js/app_config.js', 'w') as f:
        f.write(js)


def less():
    for path in glob('less/*.less'):
        filename = os.path.split(path)[-1]
        name = os.path.splitext(filename)[0]
        out_path = 'www/css/%s.less.css' % name

        os.system('%s/lessc %s %s' % (app_config.APPS_NODE_PATH, path, out_path))


def jst():
    os.system('%s/jst --template underscore jst www/js/templates.js' % app_config.APPS_NODE_PATH)


def render_playgrounds(playgrounds=None, compiled_includes=[]):
    """
    Render the playgrounds pages.
    """
    from flask import g, url_for

    os.system('curl -o data/copy.xls "%s"' % app_config.COPY_URL)
    less()
    jst()

    if not playgrounds:
        playgrounds = get_active_playgrounds()

    slugs = [p.slug for p in playgrounds]

    app_config_js()

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

    NOTE: THIS HAS NOT BEEN TESTED IN A VERY LONG TIME.
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

    changed_playgrounds = []

    ACTIONS = {
        'update': process_update,
        'insert': process_insert,
        'delete-request': process_delete
    }

    for record in changes:
        action = ACTIONS[record['action']]

        playground, revisions = action(record)
        changed_playgrounds.append(playground)

        timestamp = datetime.datetime.fromtimestamp(record['timestamp']).replace(tzinfo=pytz.utc)

        # Assign the request headers to a variable.
        # Need to modify the headers to add the remote IP address which is
        # on the request object but not in the headers area.
        # Why? Because we don't want to add an additional field to the
        # Revisions model because we don't have DB migrations.
        headers = record['request']['headers']
        headers['remote_ip_address'] = record['request'].get('ip_address', None)

        Revision.create(
            timestamp=timestamp,
            action=record['action'],
            playground=playground,
            log=json.dumps(revisions),
            headers=json.dumps(headers),
            cookies=json.dumps(record['request']['cookies']),
            revision_group=revision_group
        )

    # Ensure all changes have been written to disk
    database.commit()

    return (changed_playgrounds, revision_group)


def process_insert(record):
    """
    Process a single insert record from changes.json.
    """
    playground = Playground()

    new_data = {}

    for key, value in record['playground'].items():
        if key not in ['id', 'features']:
            new_data[key] = value
            setattr(playground, key, value)

    playground.save()

    revisions = []

    for key, value in new_data.items():
        revisions.append({
            'field': key,
            'from': '',
            'to': new_data[key]
        })

    for feature in record['playground']['features']:
        PlaygroundFeature.create(
            slug=feature,
            playground=playground
        )

        revisions.append({'field': feature, 'from': 0, 'to': 1})

    return (playground, revisions)


def process_update(record):
    """
    Process a single update record from changes.json.
    """
    playground_id = record['playground']['id']

    playground = Playground.get(id=playground_id)
    old_data = copy.copy(playground.__dict__['_data'])

    new_data = {}

    for key, value in record['playground'].items():
        if key not in ['id', 'features']:
            new_data[key] = value
            setattr(playground, key, value)

    playground.save()

    old_features = []

    for feature in PlaygroundFeature.select().where(PlaygroundFeature.playground == playground_id):
        old_features.append(feature.slug)

    # Delete any features already attached to this playground.
    PlaygroundFeature.delete().where(PlaygroundFeature.playground == playground_id).execute()

    new_features = record['playground']['features']

    for slug in new_features:
        PlaygroundFeature.create(
            slug=slug,
            playground=playground
        )

    revisions = []

    for key, value in new_data.items():
        if old_data[key] != new_data[key]:
            revisions.append({
                'field': key,
                'from': old_data[key],
                'to': new_data[key]
            })

    if set(old_features) != set(new_features):
        for feature in copytext.COPY.feature_list:
            slug = feature['key']

            # Removed
            if slug in old_features and slug not in new_features:
                revisions.append({'field': slug, 'from': 1, 'to': 0})

            # Added
            if slug in new_features and slug not in old_features:
                revisions.append({'field': slug, 'from': 0, 'to': 1})

    return playground, revisions


def process_delete(record):
    """
    Create a revision from the delete requests.
    """
    playground_slug = record['playground']['slug']

    playground = Playground.get(slug=playground_slug)

    revisions = [
        { 'field': 'active', 'from': True, 'to': False},
        { 'field': 'reason', 'from': '', 'to': record['playground']['text'] }
    ]

    return (playground, revisions)


def render_sitemap():
    with app.app.test_request_context(path='sitemap.xml'):
        content = app.sitemap()

        if isinstance(content, tuple):
            content = content[0]

    with open('www/sitemap.xml', 'w') as f:
        f.write(content.encode('utf-8'))
