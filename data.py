#!/usr/bin/env python

import json
import math
import time

from csvkit import CSVKitDictReader
from peewee import *

import app_config

database = SqliteDatabase('playgrounds.db')


def unfield(field_name):
    return field_name\
        .replace('_', ' ')\
        .capitalize()\
        .replace('Zip ', 'ZIP ')\
        .replace('Url ', 'URL ')


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

    def feature_form(self):
        fields = []
        for f, slug in app_config.FEATURE_LIST:
            feature = PlaygroundFeature.select().where(
                PlaygroundFeature.playground == self.id,
                PlaygroundFeature.name == f)
            if feature.count() > 0:
                fields.append("""
                    <label>
                    <input type="checkbox" name="%s" checked="checked">
                        &nbsp;%s
                    </label>""" % (f.replace(' ', '-').lower(), f))
            else:
                fields.append("""
                    <label>
                    <input type="checkbox" name="%s">
                    &nbsp;%s</label>""" % (f.replace(' ', '-').lower(), f))
        return fields

    def create_form(self):
        fields = []
        for field in self.__dict__['_data'].keys():
            field_dict = {}
            field_dict['name'] = unfield(field)
            if field == 'id':
                field_dict['display'] = 'style="display:none"'
            field_dict['widget'] = '<input type="text" name="%s" value=""></input>' % field
            if field in app_config.PUBLIC_FIELDS:
                fields.append(field_dict)
        return fields

    def update_form(self):
        fields = []
        for field in self.__dict__['_data'].keys():
            field_dict = {}
            field_dict['name'] = unfield(field)
            if field == 'id':
                field_dict['display'] = 'style="display:none"'
            field_value = self.__dict__['_data'][field]
            if field_value == None:
                field_value = ''
            field_dict['widget'] = '<input type="text" name="%s" value="%s"></input>' % (field, field_value)
            if field in app_config.PUBLIC_FIELDS:
                fields.append(field_dict)
        return fields

    def sdf(self):
        """
        Return a representation of this playground in CloudSearch SDF format.
        """
        sdf = {
            'type': 'add',
            'id': '%s_%i' % (app_config.DEPLOYMENT_TARGET, self.id),
            'version': int(time.time()),
            'lang': 'en',
            'fields': {
                'deployment_target': app_config.DEPLOYMENT_TARGET,
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
            sdf['fields']['latitude'] = abs(int((self.latitude + app_config.CLOUD_SEARCH_DEG_OFFSET) * app_config.CLOUD_SEARCH_DEG_SCALE))
            sdf['fields']['longitude'] = abs(int((self.longitude + app_config.CLOUD_SEARCH_DEG_OFFSET) * app_config.CLOUD_SEARCH_DEG_SCALE))

        return sdf

    def delete_sdf(self):
        sdf = {
            'type': 'delete',
            'id': '%s_%i' % (app_config.DEPLOYMENT_TARGET, self.id),
            'version': int(time.time())
        }

        return sdf


class PlaygroundFeature(Model):
    """
    A feature at a single playground.
    Feature names should be limited to app_config.FEATURE_LIST
    """
    name = TextField()
    slug = TextField()
    description = TextField(null=True)
    playground = ForeignKeyField(Playground, cascade=False)

    class Meta:
        database = database


def clear_playgrounds():
    """
    Clear playground data from sqlite.
    """
    try:
        Playground.drop_table()
        PlaygroundFeature.drop_table()
    except:
        pass

def load_playgrounds():
    """
    Load playground data from the CSV into sqlite.
    """
    Playground.create_table()
    PlaygroundFeature.create_table()

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

def parse_inserts():
    with open('inserts.json', 'r') as jsonfile:
        inserts = json.loads(jsonfile.read())
    for record in inserts:
        update_dict = {}
        for key, value in record['playground'].items():
            if key not in ['id', 'timestamp', 'features']:
                if value == '':
                    value = None
                update_dict[key] = value

        playground = Playground.get(id=int(record['playground']['id']))
        playground.update(**update_dict).execute()

        PlaygroundFeature.delete().where(PlaygroundFeature.playground == playground.id).execute()

        features = record['playground']['features']

        if len(features) > 0:
            for feature in features:
                try:
                    PlaygroundFeature.get(PlaygroundFeature.slug == feature)
                except PlaygroundFeature.DoesNotExist:
                    for f, slug in app_config.FEATURE_LIST:
                        if feature == slug:
                            PlaygroundFeature(slug=slug, name=f, playground=playground).save()
