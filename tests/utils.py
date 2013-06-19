#!/usr/bin/env python

import os

import data

TEST_PLAYGROUNDS_CSV = 'tests/data/test_playgrounds.csv'

def load_test_playgrounds():
    data.delete_tables()
    data.create_tables()
    data.load_playgrounds(TEST_PLAYGROUNDS_CSV)

def backup_updates_json():
    try:
        os.rename('data/updates.json',  'data/updates.json.bak')
    except OSError:
        pass

def restore_updates_json():
    try:
        os.rename('data/updates.json.bak', 'data/updates.json')
    except OSError:
        pass

def backup_inserts_json():
    try:
        os.rename('data/inserts.json',  'data/inserts.json.bak')
    except OSError:
        pass

def restore_inserts_json():
    try:
        os.rename('data/inserts.json.bak', 'data/inserts.json')
    except OSError:
        pass
