#!/usr/bin/env python

import math
import time

from csvkit import CSVKitDictReader
from peewee import *

database = SqliteDatabase('playgrounds.db')

class Playground(Model):
    """
    The playground model for the sqlite database.
    """
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

    def sdf(self):
        """
        Return a representation of this playground in CloudSearch SDF format.
        """
        sdf = {
            'type': 'add',
            'id': self.id,
            'version': int(time.time()),
            'lang': 'en',
            'fields': {
                'name': self.name,
                'facility': self.facility,
                'agency': self.agency,
                'owner': self.owner,
                'owner_type': self.owner_type,
                'full_text': ' | '.join([self.name, self.facility, self.agency, self.owner])
            }
        }

        if self.latitude:
            sdf['fields']['latitude'] = int(self.latitude * 111133)
            sdf['fields']['longitude'] = int(self.longitude * (math.cos(self.latitude) * 111133))

        return sdf

def clear_playgrounds():
    """
    Clear playground data from sqlite.
    """
    try:
        Playground.drop_table()
    except:
        pass

def load_playgrounds():
    """
    Load playground data from the CSV into sqlite.
    """
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

