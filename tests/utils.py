#!/usr/bin/env python

import os

import data
import models

TEST_PLAYGROUNDS_CSV = 'tests/data/test_playgrounds.csv'

def load_test_playgrounds():
    models.delete_tables()
    models.create_tables()
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
