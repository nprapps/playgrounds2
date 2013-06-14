#!/usr/bin/env python

import json
import os
import unittest

from flask import url_for

import app_config
import public_app

class IndexTestCase(unittest.TestCase):
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
        
        response = self.client.post(url_for('_api'), data={
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
        
        response = self.client.post(url_for('_api'), data={
            'id': 0,
            'name': 'NEW NAME'
        })

        response = self.client.post(url_for('_api'), data={
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


if __name__ == '__main__':
    unittest.main()
