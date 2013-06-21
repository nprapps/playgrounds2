#!/usr/bin/env python

import json
import unittest

import boto
from boto.s3.key import Key
from flask import url_for

import app_config
import models
from models import Playground
import public_app
import tests.utils as utils

class ApiTestCase(unittest.TestCase):
    """
    Test the index page.
    """
    def setUp(self):
        public_app.app.config['TESTING'] = True
        self.client = public_app.app.test_client()

        utils.backup_changes_json()

        self.request_context = public_app.app.test_request_context()
        self.request_context.push()

    def tearDown(self):
        self.request_context.pop()

        utils.restore_changes_json()

    def test_update_playground(self):
        utils.load_test_playgrounds()

        response = self.client.post(url_for('update_playground'), data={
            'id': 1,
            'name': 'NEW NAME'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/%s.html' % (app_config.S3_BASE_URL, Playground.get(id=1).slug)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        with open('data/changes.json') as f:
            updates = json.load(f)

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]['action'], 'update')
        self.assertEqual(updates[0]['playground']['id'], 1)
        self.assertEqual(updates[0]['playground']['name'], 'NEW NAME')

    def test_update_two_playgrounds(self):
        utils.load_test_playgrounds()

        response = self.client.post(url_for('update_playground'), data={
            'id': 1,
            'name': 'NEW NAME'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/%s.html' % (app_config.S3_BASE_URL, Playground.get(id=1).slug)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        response = self.client.post(url_for('update_playground'), data={
            'id': 2,
            'name': 'ANOTHER NEW NAME'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/%s.html' % (app_config.S3_BASE_URL, Playground.get(id=2).slug)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        with open('data/changes.json') as f:
            updates = json.load(f)

        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[0]['action'], 'update')
        self.assertEqual(updates[0]['playground']['id'], 1)
        self.assertEqual(updates[0]['playground']['name'], 'NEW NAME')
        self.assertEqual(updates[1]['action'], 'update')
        self.assertEqual(updates[1]['playground']['id'], 2)
        self.assertEqual(updates[1]['playground']['name'], 'ANOTHER NEW NAME')

    def test_delete_playground(self):
        utils.load_test_playgrounds()

        response = self.client.post(url_for('delete_playground'), data={
            "slug": "strong-reach-playground-bowdon-ga",
            "text": "TEST TEXT FOR REASONING."
        })

        self.assertEqual(response.status_code, 302)
        redirect_url = '%s/playground/%s.html?action=deleting_thanks' % (app_config.S3_BASE_URL, "strong-reach-playground-bowdon-ga")
        self.assertEqual(response.headers['location'],redirect_url)

    def test_delete_playground_confirm(self):
        utils.load_test_playgrounds()

        app_config.configure_targets('staging')

        s3 = boto.connect_s3()
        bucket = s3.get_bucket(app_config.S3_BUCKETS[0])
        k = Key(bucket)
        k.key = '%s/playground/%s.html' % (app_config.PROJECT_SLUG, Playground.get(id=1).slug)
        k.set_contents_from_string('foo')

        response = self.client.get(url_for('delete_playground_confirm', playground_slug=Playground.get(id=1).slug))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Playground.get(id=1).active)

        self.assertIsNone(bucket.get_key(k.key))
        app_config.configure_targets(None)

    def test_add_playground(self):
        models.delete_tables()
        models.create_tables()

        response = self.client.post(url_for('insert_playground'), data={
            'name': 'NEW PLAYGROUND'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/create.html' % (app_config.S3_BASE_URL)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        with open('data/changes.json') as f:
            inserts = json.load(f)

        self.assertEqual(len(inserts), 1)
        self.assertEqual(inserts[0]['action'], 'insert')
        self.assertEqual(inserts[0]['playground']['name'], 'NEW PLAYGROUND')

if __name__ == '__main__':
    unittest.main()
