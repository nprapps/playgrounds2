#!/usr/bin/env python

import json
import math
import re
import time

import boto
from boto.s3.bucket import Bucket
from boto.s3.key import Key
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase
import requests

import app_config


US_STATES = (('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('DC', 'District of Columbia'), ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'))


database = SqliteExtDatabase('playgrounds.db')


def delete_tables():
    """
    Clear playground data from sqlite.
    """
    try:
        Playground.drop_table()
        PlaygroundFeature.drop_table()
        Revision.drop_table()
    except:
        pass


def create_tables():
    """
    Create database tables for each model.
    """
    Playground.create_table()
    PlaygroundFeature.create_table()
    Revision.create_table()


class Playground(Model):
    """
    The playground model for the sqlite database.
    """
    slug = CharField()

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

    active = BooleanField(default=True)

    class Meta:
        database = database

    @property
    def display_name(self):
        """
        Generate a display-friendly name for this playground.
        """
        if self.name:
            return self.name

        if self.facility:
            return 'Playground at %s'  % self.facility

        return 'Unnamed Playground'

    def save(self, *args, **kwargs):
        """
        Slugify before saving!
        """
        if not self.slug:
            self.slugify()

        super(Playground, self).save(*args, **kwargs)

    def deactivate(self):
        """
        Deactivate (instead of deleting) a model instance. Also delete from
        S3 and CloudSearch.
        """
        # Deactivate playgrounds flagged for removal and commit it to the database
        self.active = False
        self.save()

        # Reach into the bowels of S3 and Cloudsearch
        self.remove_from_s3()
        self.remove_from_search_index()

    def remove_from_s3(self):
        """
        Removes file for this model instance from S3
        """
        conn = boto.connect_s3() 

        # loop over buckets, we have more than one, and remove this playground.
        for bucket in app_config.S3_BUCKETS:
            b = Bucket(conn, bucket)
            k = Key(b)
            k.key = '%s/playground/%s.html' % (app_config.PROJECT_SLUG, self.slug)
            b.delete_key(k)

    def remove_from_search_index(self):
        """
        Removes a playground from search index
        """
        sdf = self.delete_sdf()
        payload = json.dumps([sdf])

        if len(payload) > 5000 * 1024:
            print 'Exceeded 5MB limit for SDF uploads!'
            return

        requests.post('http://%s/2011-02-01/documents/batch' % app_config.CLOUD_SEARCH_DOC_DOMAIN, data=payload, headers={ 'Content-Type': 'application/json' })

    def slugify(self):
        """
        Generate a slug for this playground.
        """
        bits = []

        for field in ['display_name', 'city', 'state']:
            attr = getattr(self, field)

            if attr:
                attr = attr.lower()
                attr = re.sub(r"[^\w\s]", '', attr)
                attr = re.sub(r"\s+", '-', attr)

                bits.append(attr)

        base_slug = '-'.join(bits)

        slug = base_slug
        i = 1

        while Playground.select().where(Playground.slug == slug).count():
            i += 1
            slug = '%s-%i' % (base_slug, i)

        self.slug = slug

    def feature_form(self):
        """
        Constructs the features form for this playground.
        Shows the current state of attached features, if any exist.
        """
        fields = []

        for slug, details in app_config.FEATURES.items():
            instances = PlaygroundFeature.select().where(
                PlaygroundFeature.playground == self.id,
                PlaygroundFeature.slug == slug)

            checked = 'checked="checked"' if instances.count() > 0 else ''

            fields.append("""
                <input type="checkbox" name="%s" %s>
                <label class="checkbox">%s
                </label>
            """ % (slug, checked, details['name']))

        return fields

    def create_form(self):
        """
        Construct the creation form for this playground.
        """
        fields = []
        for field in self.__dict__['_data'].keys():
            field_dict = {}
            field_dict['name'] = unfield(field)
            field_value = ''
            if field == 'id':
                field_dict['display'] = 'style="display:none"'
                field_dict['widget'] = '<input class="input" type="text" name="%s" value=""></input>' % field
            elif field == 'remarks':
                field_dict['widget'] = '<textarea class="input-block-level input" name="%s" rows="10">%s</textarea>' % (field, field_value)
            # elif field == 'state':
            #     options = ''
            #     for abbrev, name in US_STATES:
            #         options += '<option class="input" value="%s" >%s</option>' % (abbrev, abbrev)
            #     field_dict['widget'] = '<select name="state">%s</select>' % options
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
            if field in ['slug', 'id']:
                field_dict['display'] = 'style="display:none"'
                field_dict['widget'] = '<input class="input" type="text" name="%s" value="%s" data-changed="true"></input>' % (field, field_value)
            elif field == 'remarks':
                field_dict['widget'] = '<textarea class="input-block-level input" name="%s" rows="10">%s</textarea>' % (field, field_value)
            # elif field == 'state':
            #     options = ''
            #     for abbrev, name in US_STATES:
            #         if self.state == abbrev:
            #             options += '<option class="input" value="%s" selected>%s</option>' % (abbrev, abbrev)
            #         else:
            #             options += '<option class="input" value="%s">%s</option>' % (abbrev, abbrev)
            #     field_dict['widget'] = '<select name="state">%s</select>' % options
            else:
                field_dict['widget'] = '<input class="input-block-level input" type="text" name="%s" value="%s"></input>' % (field, field_value)
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
                'name': self.name or '',
                'city': self.city or '',
                'state': self.state or '',
                'zip_code': self.zip_code or '',
                'facility': self.facility or '',
                'agency': self.agency or '',
                'owner': self.owner or '',
                'owner_type': self.owner_type or '',
                'public_remarks': self.public_remarks or '',
                'full_text': ' | '.join([self.name, self.city or '', self.state or '', self.agency or '', self.owner or '', self.public_remarks or '']),
                'slug': self.slug,
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
        """
        Create a CloudSearch SDF payload suitable for deleting this playground.
        """
        sdf = {
            'type': 'delete',
            'id': '%s_%i' % (app_config.DEPLOYMENT_TARGET, self.id),
            'version': int(time.time())
        }

        return sdf

    def nearby(self, n):
        """
        Return a list of playgrounds near this one.o
        
        See below for the implementation of the SQL distance algorithm.
        """
        if not self.latitude or not self.longitude:
            return []

        return Playground.raw('SELECT *, distance(?, ?, latitude, longitude) as distance FROM playground WHERE distance IS NOT NULL AND id <> ? ORDER BY distance ASC LIMIT ?', self.latitude, self.longitude, self.id, n)


@database.func()
def distance(lat1, lng1, lat2, lng2):
    """
    Use spherical law of cosines to compute distance.
    """
    if not lat1 or not lng1 or not lat2 or not lng2:
        return None

    if lat1 == lat2 and lng1 == lng2:
        return 0

    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    return 3958.761 * math.acos(math.sin(lat1_rad) * math.sin(lat2_rad) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lng2_rad - lng1_rad))


def unfield(field_name):
    """
    Turn field names into pretty titles.
    """
    return field_name\
        .replace('_', ' ')\
        .capitalize()\
        .replace('Zip ', 'ZIP ')\
        .replace('Url ', 'URL ')


def get_active_playgrounds():
    """
    A function which acts like a Django model manger.
    Returns only active playgrounds.
    Can chain .where() clauses against this, e.g.,
    all active playgrounds in NY:

        get_active_playgrounds().where(Playground.state == 'NY')
    """
    return Playground.select().where(Playground.active == True)


class PlaygroundFeature(Model):
    """
    A feature at a single playground.
    Feature names should be limited to app_config.FEATURES.keys()
    """
    slug = CharField()
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
    action = CharField()
    log = TextField()
    playground = ForeignKeyField(Playground, cascade=False)
    headers = TextField(null=True)
    cookies = TextField(null=True)
    revision_group = IntegerField()

    class Meta:
        database = database

    def get_log(self):
        return json.loads(self.log)

    def get_headers(self):
        return json.loads(self.headers)

    def get_cookies(self):
        return json.loads(self.cookies)

