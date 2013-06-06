#!/usr/bin/env python

from csvkit import CSVKitDictReader
from peewee import *

database = SqliteDatabase('playgrounds.db')

class Playground(Model):
    name = CharField()

    class Meta:
        database = database

def clear_playgrounds():
    try:
        Playground.drop_table()
    except:
        pass

def load_playgrounds():
    Playground.create_table()

    with open('data/playgrounds.csv') as f:
        rows = CSVKitDictReader(f)

        for row in rows:
            Playground.create(
                name = row['Playground Name ']
            )
