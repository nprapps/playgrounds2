#!/usr/bin/env python

import unittest

from csvkit import CSVKitDictReader
import peewee

import data
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

        playgrounds = data.Playground.select()

        self.assertEqual(len(non_duplicate), playgrounds.count())

class UpdatesTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_process_updates_simple(self):
        utils.load_test_playgrounds()

        updated_playground_slugs, revision_group = data.process_updates('tests/data/test_updates_simple.json')

        self.assertEqual(len(updated_playground_slugs), 1)

        playground = data.Playground.select().where(data.Playground.slug == updated_playground_slugs[0])[0]
        self.assertEqual(playground.id, 1) 
        self.assertEqual(playground.name, 'NEW NAME')

        revisions = data.Revision.select().where(data.Revision.revision_group == revision_group)

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

    def test_process_updates_features(self):
        utils.load_test_playgrounds()

        data.PlaygroundFeature.create(
            name='Transfer stations to play components',
            slug='transfer-stations-to-play-components',
            playground=data.Playground.get(id=1)
        )

        # JSON adds one feature and removes the one just created
        updated_playground_slugs, revision_group = data.process_updates('tests/data/test_updates_features.json')

        features = data.PlaygroundFeature.select().where(data.PlaygroundFeature.playground == 1)

        self.assertEqual(features.count(), 1)

        feature = features[0]
        self.assertEqual(feature.slug, 'smooth-surface-throughout')
        

class InsertsTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_process_inserts(self):
        # TKTK
        pass

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

        playground = data.Playground.get(id=1)
        
        log = '''[{
            "field": "name",
            "from": "%s",
            "to": "Test Playground" 
        }]''' % playground.name

        data.Revision(
            playground=playground,
            timestamp=0,
            log=log,
            headers='',
            cookies='',
            revision_group=1
        ).save()

        body = data.prepare_email(1)
        
        self.assertTrue(body.find(playground.name) >= 0)

if __name__ == '__main__':
    unittest.main()
