#!/usr/bin/env python

import json
import unittest

from flask import url_for

import app
import app_config
from models import Playground
import tests.utils as utils


class ViewsTestCase(unittest.TestCase):
    """
    Test the index page.
    """
    def setUp(self):
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()
        self.request_context = app.app.test_request_context()
        self.request_context.push()

    def tearDown(self):
        self.request_context.pop()

    def test_index_exists(self):
        response = self.client.get(url_for('index'))

        assert app_config.PROJECT_NAME in response.data

    def test_sitemap_exists(self):
        response = self.client.get(url_for('sitemap'))

        assert app_config.PROJECT_SLUG in response.data

    def test_playground_exists(self):
        utils.load_test_playgrounds()

        playground = Playground.get(id=1)

        response = self.client.get(url_for('_playground', playground_slug=playground.slug))

        assert playground.display_name in response.data

    def test_playground_create_exists(self):
        response = self.client.get(url_for('playground_create'))

        assert 'playground' in response.data


class AppConfigTestCase(unittest.TestCase):
    """
    Testing dynamic conversion of Python app_config into Javascript.
    """
    def setUp(self):
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()

    def parse_data(self, response):
        """
        Trim leading variable declaration and load JSON data.
        """
        data = response.data.split('\n')[0]
        data = data.strip(';')[20:]
        return json.loads(data)

    def test_app_config_staging(self):
        response = self.client.get('/js/app_config.js')

        data = self.parse_data(response)

        assert data['DEBUG'] is True

    def test_app_config_production(self):
        app_config.configure_targets('production')

        response = self.client.get('/js/app_config.js')

        data = self.parse_data(response)

        assert data['DEBUG'] is False

        app_config.configure_targets('staging')

if __name__ == '__main__':
    unittest.main()
