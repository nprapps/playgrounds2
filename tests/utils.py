#!/usr/bin/env python

import os

import data

TEST_PLAYGROUNDS_CSV = 'tests/data/test_playgrounds.csv'

def load_test_playgrounds():
    data.delete_tables()
    data.create_tables()
    data.load_playgrounds(TEST_PLAYGROUNDS_CSV)

def backup_changes_json():
    try:
        os.rename('data/changes.json',  'data/changes.json.bak')
    except OSError:
        pass

def restore_changes_json():
    try:
        os.rename('data/changes.json.bak', 'data/changes.json')
    except OSError:
        pass
