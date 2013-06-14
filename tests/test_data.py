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

if __name__ == '__main__':
    unittest.main()
