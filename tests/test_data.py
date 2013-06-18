#!/usr/bin/env python

import unittest

from csvkit import CSVKitDictReader
import peewee

import data
import tests.utils as utils

class UpdatesTestCase(unittest.TestCase):
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
