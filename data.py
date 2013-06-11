#!/usr/bin/env python

import math
import time

from csvkit import CSVKitDictReader
from peewee import *

import app_config

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
                'city': self.city,
                'state': self.state,
                'zip_code': self.zip_code,
                'facility': self.facility,
                'agency': self.agency,
                'owner': self.owner,
                'owner_type': self.owner_type,
                'full_text': ' | '.join([self.name, self.city, self. state, self.facility, self.agency, self.owner])
            }
        }

        if self.latitude:
            # Convert to radians, scale up, convert to int and take the absolute value,
            # All in the service of storing as an accurate uint
            sdf['fields']['latitude'] = abs(int(self.latitude * math.pi / 180 * app_config.CLOUD_SEARCH_RADIANS_SCALE))
            sdf['fields']['longitude'] = abs(int(self.longitude * math.pi / 180 * app_config.CLOUD_SEARCH_RADIANS_SCALE))

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

