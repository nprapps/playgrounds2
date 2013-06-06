#!/usr/bin/env python

from csvkit import CSVKitDictReader
from peewee import *

database = SqliteDatabase('playgrounds.db')

class Playground(Model):
    name = CharField()
    facility = CharField(null=True)
    facility_type = CharField(null=True)

    address = CharField(null=True)
    city = CharField(null=True)
    state = CharField(null=True)
    zip_code = CharField(null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
 
    agency = CharField(null=True)
    agency_type = CharField(null=True)

    owner = CharField(null=True)
    owner_type = CharField(null=True)
    remarks = TextField(null=True)
    public_remarks = TextField(null=True)

    url = CharField(null=True)
    entry = CharField(null=True)
    source = CharField(null=True)

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
            if row['Duplicate'] == 'TRUE':
                print 'Skipping duplicate: %s' % row['NAME']
                continue

            Playground.create(
                nprid=row['NPRID'],
                name=row['NAME'],
                facility=row['FACILITY'],
                facility_type=row['FACILITY_TYPE'],
                address=row['ADDRESS'],
                city=row['CITY'],
                state=row['STATE'],
                zip_code=row['ZIP'],
                longitude=float(row['LONGITUDE']) if row['LONGITUDE'] else None,
                latitude=float(row['LATITUDE']) if row['LATITUDE'] else None,
                agency=row['Agency'],
                agency_type=row['AgencyType'],
                owner=row['OWNER'],
                owner_type=row['OWNER_TYPE'],
                remarks=row['REMARKS'],
                public_remarks=row['PubRermarks'],
                url=row['url'],
                entry=row['Entry'],
                source=row['Source']
            )
