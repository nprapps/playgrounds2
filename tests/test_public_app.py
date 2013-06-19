#!/usr/bin/env python

import json
import unittest

import boto
# import boto.cloudsearch
from boto.s3.key import Key
from flask import url_for

import app_config
import data
import public_app
import tests.utils as utils

class ApiTestCase(unittest.TestCase):
    """
    Test the index page.
    """
    def setUp(self):
        public_app.app.config['TESTING'] = True
        self.client = public_app.app.test_client()

        utils.backup_updates_json()
        utils.backup_inserts_json()

        self.request_context = public_app.app.test_request_context()
        self.request_context.push()

    def tearDown(self):
        self.request_context.pop()

        utils.restore_updates_json()
        utils.restore_inserts_json()

    def test_edit_playground(self):
        utils.load_test_playgrounds()

        response = self.client.post(url_for('edit_playground'), data={
            'id': 1,
            'name': 'NEW NAME'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/%s.html' % (app_config.S3_BASE_URL, data.Playground.get(id=1).slug)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        with open('data/updates.json') as f:
            updates = json.load(f)

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]['playground']['id'], 1)
        self.assertEqual(updates[0]['playground']['name'], 'NEW NAME')

    def test_edit_two_playgrounds(self):
        utils.load_test_playgrounds()

        response = self.client.post(url_for('edit_playground'), data={
            'id': 1,
            'name': 'NEW NAME'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/%s.html' % (app_config.S3_BASE_URL, data.Playground.get(id=1).slug)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        response = self.client.post(url_for('edit_playground'), data={
            'id': 2,
            'name': 'ANOTHER NEW NAME' 
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/%s.html' % (app_config.S3_BASE_URL, data.Playground.get(id=2).slug)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        with open('data/updates.json') as f:
            updates = json.load(f)

        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[0]['playground']['id'], 1)
        self.assertEqual(updates[0]['playground']['name'], 'NEW NAME')
        self.assertEqual(updates[1]['playground']['id'], 2)
        self.assertEqual(updates[1]['playground']['name'], 'ANOTHER NEW NAME')

    def test_delete_playground(self):
        utils.load_test_playgrounds()

        response = self.client.post(url_for('delete_playground'), data={
            'id': 0
        })

        self.assertEqual(response.status_code, 302)
        redirect_url = '%s/playground/%s.html' % (app_config.S3_URL, data.Playground.get(id=0).slug)
        self.assertEqual(response.headers['location'],redirect_url)
        
        self.assertGreaterEqual(data.DeleteRequest.select().where(data.DeleteRequest.playground == 0).count(), 1)

    def test_delete_playground_confirm(self):
        utils.load_test_playgrounds()

        app_config.configure_targets('staging')
        
        s3 = boto.connect_s3()
        bucket = s3.get_bucket(app_config.S3_BUCKETS[0])
        k = Key(bucket)
        k.key = '%s/playground/%s.html' % (app_config.PROJECT_SLUG, data.Playground.get(id=0).slug)
        k.set_contents_from_string('foo')

        response = self.client.post(url_for('delete_playground_confirm'), data={
            'id': 0
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.Playground.get(id=0).deleted)

        self.assertIsNone(bucket.get_key(k.key))
        app_config.configure_targets(None)
        
        # cs = boto.cloudsearch.connect_to_region('us-west-2')

    def test_add_playground(self):
        data.delete_tables()
        data.create_tables()

        response = self.client.post(url_for('new_playground'), data={
            'name': 'NEW PLAYGROUND'
        })

        self.assertEqual(response.status_code, 302)

        redirect_url = '%s/playground/create.html' % (app_config.S3_BASE_URL)
        self.assertEqual(response.headers['Location'].split('?')[0], redirect_url)

        with open('data/inserts.json') as f:
            inserts = json.load(f)

        self.assertEqual(len(inserts), 1)
        self.assertEqual(inserts[0]['playground']['name'], 'NEW PLAYGROUND')

if __name__ == '__main__':
    unittest.main()
