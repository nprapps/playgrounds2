#!/usr/bin/env python

import datetime
import json
import time
import unittest

from csvkit import CSVKitDictReader
import peewee
import pytz
import requests

import app_config
import app
import data
import models
from models import Playground, PlaygroundFeature, Revision
import tests.utils as utils


class PlaygroundsTestCase(unittest.TestCase):
    """
    Test the index page.
    """
    def setUp(self):
        peewee.logger.setLevel(100)

    def tearDown(self):
        pass

    def test_load_playgrounds(self):
        with open('tests/data/test_playgrounds.csv') as f:
            reader = CSVKitDictReader(f)
            rows = list(reader)

        non_duplicate = filter(lambda r: r['Duplicate'] != 'TRUE', rows)

        utils.load_test_playgrounds()

        playgrounds = Playground.select()

        self.assertEqual(len(non_duplicate), playgrounds.count())


class DeletesTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_process_deletes(self):
        """
        Test the process_deletes bits.
        """

        # Test process_changes()
        utils.load_test_playgrounds()

        deleted_playgrounds, revision_group = data.process_changes('tests/data/test_deletes.json')

        self.assertEqual(len(deleted_playgrounds), 0)

        # Test process_delete() itself.
        with open('tests/data/test_deletes.json', 'r') as jsonfile:
            test_deletes = json.loads(jsonfile.read())

        playground, revisions = data.process_delete(test_deletes[0])

        expected_id = 1
        expected_revisions = [
            {"field": "active", "from": True, "to": False},
            {"field": "reason", "from": "", "to": "This playground doesn't appear to be accessible in any way whatsoever."}
        ]

        self.assertEqual(playground.id, expected_id)
        self.assertEqual(revisions, expected_revisions)

    def test_remove_from_search_index(self):
        app_config.configure_targets('staging')

        utils.load_test_playgrounds()

        playground = Playground.select()[0]

        sdf = playground.sdf()
        sdf['id'] = 'test_%i' % playground.id
        sdf['fields']['name'] = 'THIS IS NOT A PLAYGROUND NAME axerqwak'
        sdf['fields']['deployment_target'] = 'test'

        response = requests.post('http://%s/2011-02-01/documents/batch' % app_config.CLOUD_SEARCH_DOC_DOMAIN, data=json.dumps([sdf]), headers={ 'Content-Type': 'application/json' })

        self.assertEqual(response.status_code, 200)

        # Monkey patch delete_sdf to so it return test id
        delete_sdf = playground.delete_sdf()
        delete_sdf['id'] = 'test_%i' % playground.id
        delete_sdf['version'] = sdf['version'] + 1

        old_func = playground.delete_sdf
        playground.delete_sdf = lambda: delete_sdf

        playground.remove_from_search_index()

        playground.delete_sdf = old_func

        response = requests.get('http://%s/2011-02-01/search' % app_config.CLOUD_SEARCH_DOMAIN, params={ 'q': 'axerqwak' }, headers={ 'Cache-Control': 'revalidate' })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['hits']['found'], 0)

        app_config.configure_targets(None)


class UpdatesTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_process_updates_simple(self):
        utils.load_test_playgrounds()

        updated_playgrounds, revision_group = data.process_changes('tests/data/test_updates_simple.json')

        self.assertEqual(len(updated_playgrounds), 1)

        playground = Playground.select().where(Playground.id == updated_playgrounds[0].id)[0]
        self.assertEqual(playground.id, 1)
        self.assertEqual(playground.name, 'NEW NAME')

        revisions = Revision.select().where(Revision.revision_group == revision_group)

        self.assertEqual(revisions.count(), 1)

        revision = revisions[0]
        self.assertEqual(revision.playground.id, playground.id)

        log = revision.get_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['field'], 'name')
        self.assertEqual(log[0]['from'], 'Strong Reach Playground')
        self.assertEqual(log[0]['to'], 'NEW NAME')

        headers = revision.get_headers()
        self.assertEqual(headers['content_length'], '18')
        self.assertEqual(headers['host'], 'localhost')

        cookies = revision.get_cookies()
        self.assertEqual(len(cookies), 0)

    def test_process_update_only_one(self):
        utils.load_test_playgrounds()

        updated_playgrounds, revision_group = data.process_changes('tests/data/test_updates_simple.json')

        self.assertEqual(len(updated_playgrounds), 1)

        playground = Playground.select().where(Playground.id != updated_playgrounds[0].id)[0]
        self.assertNotEqual(playground.id, 1)
        self.assertNotEqual(playground.name, 'NEW NAME')

    def test_process_updates_features(self):
        utils.load_test_playgrounds()

        PlaygroundFeature.create(
            slug='transfer-stations-to-play-components',
            playground=Playground.get(id=1)
        )

        # JSON adds one feature and removes the one just created
        updated_playgrounds, revision_group = data.process_changes('tests/data/test_updates_features.json')

        features = PlaygroundFeature.select().where(PlaygroundFeature.playground == 1)

        self.assertEqual(features.count(), 1)

        feature = features[0]
        self.assertEqual(feature.slug, 'smooth-surface-throughout')


class InsertsTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_process_inserts(self):
        models.delete_tables()
        models.create_tables()

        new_playgrounds, revision_group = data.process_changes('tests/data/test_inserts.json')

        self.assertEqual(len(new_playgrounds), 1)

        playground = Playground.select().where(Playground.id == new_playgrounds[0].id)[0]
        self.assertEqual(playground.name, 'NEW NAME')

        revisions = Revision.select().where(Revision.revision_group == revision_group)

        self.assertEqual(revisions.count(), 1)

        revision = revisions[0]
        self.assertEqual(revision.playground.id, playground.id)

        log = revision.get_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['field'], 'name')
        self.assertEqual(log[0]['from'], '')
        self.assertEqual(log[0]['to'], 'NEW NAME')

        headers = revision.get_headers()
        self.assertEqual(headers['content_length'], '18')
        self.assertEqual(headers['host'], 'localhost')

        cookies = revision.get_cookies()


class EmailTestCase(unittest.TestCase):
    """
    Test send revisions email.
    """
    def setUp(self):
        peewee.logger.setLevel(100)

    def tearDown(self):
        pass

    def test_prepare_email(self):
        utils.load_test_playgrounds()

        playground = Playground.get(id=1)

        log = '''[{
            "field": "name",
            "from": "%s",
            "to": "Test Playground"
        }]''' % playground.name

        Revision(
            action='update',
            timestamp=time.mktime(datetime.datetime.now(pytz.utc).timetuple()),
            playground=playground,
            log=log,
            headers='',
            cookies='',
            revision_group=1
        ).save()

        body = app._prepare_email(1)

        self.assertTrue(body.find(playground.name) >= 0)

if __name__ == '__main__':
    unittest.main()
