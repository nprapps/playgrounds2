#!/usr/bin/env python

import json
import math
import time

from csvkit import CSVKitDictReader
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase

import app_config

database = SqliteExtDatabase('playgrounds.db')


def unfield(field_name):
    """
    Turn field names into pretty titles.
    """
    return field_name\
        .replace('_', ' ')\
        .capitalize()\
        .replace('Zip ', 'ZIP ')\
        .replace('Url ', 'URL ')


@database.func()
def distance(lat1, lng1, lat2, lng2):
    """
    Use spherical law of cosines to compute distance.
    """
    if not lat1 or not lng1 or not lat2 or not lng2:
        return None

    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    return 3958.761 * math.acos(math.sin(lat1_rad) * math.sin(lat2_rad) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lng2_rad - lng1_rad))


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
        """
        Constructs the features form for this playground.
        Shows the current state of attached features, if any exist.
        """
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
        """
        Construct the creation form for this playground.
        """
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
        """
        Construct the update form for this playground.
        """
        fields = []
        for field in self.__dict__['_data'].keys():
            field_dict = {}
            field_dict['name'] = unfield(field)
            field_value = self.__dict__['_data'][field]
            if field_value == None:
                field_value = ''
            if field == 'id':
                field_dict['display'] = 'style="display:none"'
                field_dict['widget'] = '<input type="text" name="%s" value="%s" data-changed="true"></input>' % (field, field_value)
            else:
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
                'full_text': ' | '.join([self.name, self.city, self. state, self.facility, self.agency, self.owner]),
                'display_name': self.display_name
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

    @property
    def display_name(self):
        if self.name:
            return self.name

        if self.facility:
            return 'Playground at %s'  % self.facility

        return 'Unnamed Playground'

    def nearby(self, n):
        if not self.latitude or not self.longitude:
            return []

        return Playground.raw('SELECT *, distance(?, ?, latitude, longitude) as distance FROM playground WHERE distance IS NOT NULL AND id <> ? ORDER BY distance ASC LIMIT ?', self.latitude, self.longitude, self.id, n)


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


class Revision(Model):
    """
    A single atomic revision for a single playground.
    Log should a list of dictionaries, one dictionary
    for every field which has changed during the revision.
    Each feature also becomes a similar dictionary, except
    that the from/to fields become 0 or 1, depending on if
    a feature was removed or added.
    [{
        "field": "zip_code",
        "from": "20005",
        "to": "20006"
    }, {
        "field": "sound-play-components",
        "from": 0,
        "to": 1
    }]
    """
    timestamp = IntegerField()
    log = TextField()
    playground = ForeignKeyField(Playground, cascade=False)
    headers = TextField(null=True)
    cookies = TextField(null=True)

    class Meta:
        database = database

    def get_log(self):
        return json.loads(self.log)

    def get_headers(self):
        return json.loads(self.headers)

    def get_cookies(self):
        return json.loads(self.cookies)


def clear_playgrounds():
    """
    Clear playground data from sqlite.
    """
    try:
        Playground.drop_table()
        PlaygroundFeature.drop_table()
        Revision.drop_table()
    except:
        pass

def load_playgrounds():
    """
    Load playground data from the CSV into sqlite.
    """
    Playground.create_table()
    PlaygroundFeature.create_table()
    Revision.create_table()

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

    updated_playgrounds = []

    for record in inserts:
        update_dict = {}
        for key, value in record['playground'].items():
            if key not in ['id', 'timestamp', 'features']:
                if value == u'':
                    value = None
                update_dict[key] = value

        playground = Playground.get(id=int(record['playground']['id']))
        playground.update(**update_dict).execute()
        updated_playgrounds.append(playground.id)

        old_features = []

        for feature in PlaygroundFeature.select().where(PlaygroundFeature.playground == playground.id):
            old_features.append(feature.slug)

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

        revisions = []
        old_data = playground.__dict__['_data']
        new_data = update_dict

        for key, value in new_data.items():
            if value is None:
                new_data[key] = ''

            if old_data[key] != new_data[key]:
                revision_dict = {}
                revision_dict['field'] = key
                revision_dict['from'] = old_data[key]
                revision_dict['to'] = new_data[key]
                revisions.append(revision_dict)

        new_features = record['playground']['features']

        for f, slug in app_config.FEATURE_LIST:
            if slug in old_features:
                if f not in new_features:
                    revisions.append({"field": slug, "from": 1, "to": 0})
            if slug in new_features:
                if f not in old_features:
                    revisions.append({"field": slug, "from": 0, "to": 1})

        Revision(
            playground=playground,
            timestamp=int(record['playground']['timestamp']),
            log=json.dumps(revisions),
            headers=json.dumps(record['request']['headers']),
            cookies=json.dumps(record['request']['cookies'])
        ).save()

    return updated_playgrounds
