#!/usr/bin/env python

import json
import os
import unittest

import boto
# import boto.cloudsearch
from boto.s3.key import Key
from flask import url_for

import app_config
import data
import public_app

class ApiTestCase(unittest.TestCase):
    """
    Test the index page.
    """
    def setUp(self):
        public_app.app.config['TESTING'] = True
        self.client = public_app.app.test_client()

        self.request_context = public_app.app.test_request_context()
        self.request_context.push()

    def tearDown(self):
        self.request_context.pop()

    def test_edit_playground(self):
        try:
            os.remove('data/updates.json')
        except:
            pass
        
        response = self.client.post(url_for('edit_playground'), data={
            'id': 0,
            'name': 'NEW NAME'
        })

        self.assertEqual(response.status_code, 200)

        with open('data/updates.json') as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['playground']['id'], 0)
        self.assertEqual(data[0]['playground']['name'], 'NEW NAME')

    def test_edit_two_playgrounds(self):
        try:
            os.remove('data/updates.json')
        except:
            pass
        
        response = self.client.post(url_for('edit_playground'), data={
            'id': 0,
            'name': 'NEW NAME'
        })

        response = self.client.post(url_for('edit_playground'), data={
            'id': 1,
            'name': 'ANOTHER NEW NAME' 
        })

        self.assertEqual(response.status_code, 200)

        with open('data/updates.json') as f:
            data = json.load(f)

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['playground']['id'], 0)
        self.assertEqual(data[0]['playground']['name'], 'NEW NAME')
        self.assertEqual(data[1]['playground']['id'], 1)
        self.assertEqual(data[1]['playground']['name'], 'ANOTHER NEW NAME')

    def test_delete_playground(self):
        response = self.client.post(url_for('delete_playground'), data={
            'id': 0
        })

        self.assertEqual(response.status_code, 302)
        redirect_url = '%s/playground/%s.html' % (app_config.S3_URL, data.Playground.get(id=0).slug)
        self.assertEqual(response.headers['location'],redirect_url)
        
        self.assertGreaterEqual(data.DeleteRequest.select().where(data.DeleteRequest.playground == 0).count(), 1)

    def test_delete_playground_confirm(self):
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

if __name__ == '__main__':
    unittest.main()
