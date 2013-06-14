#!/usr/bin/env python

import unittest

from csvkit import CSVKitDictReader
import peewee

import data

class UpdatesTestCase(unittest.TestCase):
    """
    Test the index page.
    """
    def setUp(self):
        peewee.logger.setLevel(100)

    def tearDown(self):
        pass

    def test_load_playgrounds(self):
        try:
            data.clear_playgrounds()
        except:
            pass
        
        with open('data/playgrounds.csv') as f:
            reader = CSVKitDictReader(f)
            rows = list(reader)

        non_duplicate = filter(lambda r: r['Duplicate'] != 'TRUE', rows)

        data.load_playgrounds()

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
        playground = data.Playground.get(id=1)
        
        log = '''[{
            "field": "name",
            "from": "Strong Reach Playground",
            "to": "Test Playground" 
        }]'''

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
