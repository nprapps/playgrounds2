#!/usr/bin/env python

import datetime
import json
import math
import pytz
import re
import time

import boto
from boto.s3.bucket import Bucket
from boto.s3.key import Key
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase
import requests

import app_config
import copytext


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
    nprid = CharField(null=False, default='')
    name = CharField(verbose_name='Name', null=False, default='')
    facility = CharField(verbose_name='Facility', null=True)
    facility_type = CharField(verbose_name='Facility type', null=False, default='')

    address = CharField(verbose_name='Address', null=False, default='')
    city = CharField(verbose_name='City', null=False, default='')
    state = CharField(verbose_name='State', null=False, default='')
    zip_code = CharField(verbose_name='Zip Code', null=False, default='')
    latitude = FloatField(verbose_name='Latitude', null=True)
    longitude = FloatField(verbose_name='Longitude', null=True)

    agency = CharField(verbose_name='Agency', null=False, default='')
    agency_type = CharField(verbose_name='Agency type', null=False, default='')

    owner = CharField(verbose_name='Owner', null=False, default='')
    owner_type = CharField(verbose_name='Owner type', null=False, default='')
    remarks = TextField(null=False, default='')
    public_remarks = TextField(verbose_name='Remarks', null=False, default='')

    url = CharField(verbose_name='URL', null=False, default='')
    entry = CharField(null=False, default='')
    source = CharField(null=False, default='')

    active = BooleanField(default=True)

    reverse_geocoded = BooleanField(verbose_name='Reverse Geocoded', default=False)

    class Meta:
        database = database

    @property
    def features(self):
        """
        Returns the associated features of this playground.
        """

        # Get a queryset of the features.
        features = PlaygroundFeature.select().join(Playground).where(Playground.id == self.id)

        # If there aren't any, return none instead of an empty list.
        # So barbaric, empty lists.
        if features.count() > 0:
            return features

        return None

    def to_dict(self):
        """
        Dumps a playground and features as JSON.
        """
        playground = self.__dict__['_data']

        for field in ['entry', 'source', 'active', 'remarks', 'reverse_geocoded']:
            playground.pop(field)

        for k, v in playground.items():
            try:
                playground[k] = v.encode('utf-8')
            except AttributeError:
                pass

        playground['features'] = []
        if self.features:
            for feature in self.features:
                f = {}
                f['name'] = feature.slug.replace('-', ' ')
                playground['features'].append(f)

        return playground

    @property
    def percent_complete(self):
        """
        Figure out how complete this record is.
        Returns a dictionary with a percent string and a css class.
        String is truncated to two decimal points.
        """

        # Adds one to the total because we want to penalize playgrounds with no added features.
        total = len(self.__dict__['_data'].items()) + 1
        completed = 0

        # Loop over the fields. If there are fields with no data, give no credit.
        for key, value in self.__dict__['_data'].items():
            if value and value != '':
                completed += 1

        # If there's at least a single feature, give this playground one credit.
        if self.features:
            completed += 1

        # Get the floating point percentage. *Gak*
        # Also make a fancy string.
        percent = float(float(completed)/float(total)) * 100
        percent_string = "{0:.0f}".format(percent)

        # Get us a css class. If we're above 70%, we're good. Otherwise, we need help.
        klass = 'help'
        if percent > 70.0:
            klass = 'okay'

        # Return the percent string and the css class.
        return {"percent": percent_string, "class": klass}

    @property
    def display_name(self):
        """
        Generate a display-friendly name for this playground.
        """
        if self.name and self.facility:
            return '%s at %s' % (self.name, self.facility)

        if self.name:
            return self.name

        if self.facility:
            return 'Playground at %s' % self.facility

        return 'Playground'

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

    @classmethod
    def form(cls, playground=None):
        """
        Construct the form for a playground.
        """
        fields = []

        for field in cls._meta.get_field_names():
            if field in ['slug', 'entry', 'source']:
                continue

            field_dict = {}
            field_dict['name'] = display_field_name(field)

            if playground:
                field_value = getattr(playground, field)
            else:
                field_value = ''

            # Made some changes here to support the form validation JS.
            # specifically, ID needs a special widget.
            # Everything else should be an if/elif/else instead of if/if/else.
            if field == 'id':
                field_dict['display'] = 'style="display:none"'
                field_dict['widget'] = '<input class="input-block-level input" type="text" name="%s" value="%s" data-changed="true"></input>' % (field, field_value)

            # elif field == 'public_remarks':
            #     field_dict['widget'] = '<textarea class="input-block-level input" name="%s" rows="10">%s</textarea>' % (field, field_value)

            elif field == 'reverse_geocoded':
                field_dict['display'] = 'style="display:none"'
                field_dict['widget'] = '<input type="checkbox" name="%s"></input>' % (field)

            elif field in ['latitude', 'longitude', 'address', 'public_remarks', 'city', 'state', 'zip_code']:
                field_dict['display'] = 'style="display:none"'
                field_dict['widget'] = '<input class="input-block-level input" type="text" name="%s" value="%s"></input>' % (field, field_value)

            else:
                field_dict['widget'] = '<input class="input-block-level input" type="text" name="%s" value="%s"></input>' % (field, field_value)

            if field == 'facility':
                field_dict['name'] = 'At (is this in a park or school?)'

            if field in app_config.PUBLIC_FIELDS:
                fields.append(field_dict)

            order = [
                "Address",
                "City",
                "State",
                "Zip Code",
                "Name",
                "At (is this in a park or school?)",
                "URL",
                "Agency",
                "Owner",
                "Remarks",
                "Id",
                "Reverse Geocoded",
                "Slug",
                "Latitude",
                "Longitude"
            ]

            fields = sorted(fields, key=lambda x: order.index(x['name']))

        return fields

    def update_form(self):
        """
        Construct the update form for this playground.
        """
        return Playground.form(self)

    @classmethod
    def features_form(cls, playground=None):
        """
        Constructs the features form for this playground.
        Shows the current state of attached features, if any exist.
        """
        fields = []

        features = copytext.COPY.feature_list

        for feature in features:
            slug = feature['key']
            name = feature['term']

            if playground:
                instances = PlaygroundFeature.select().where(
                    PlaygroundFeature.playground == playground.id,
                    PlaygroundFeature.slug == slug)

                checked = 'checked="checked"' if instances.count() > 0 else ''
            else:
                checked = ''

            fields.append("""
                <input type="checkbox" name="%s" %s>
                <label class="checkbox">%s
                </label>
            """ % (slug, checked, name))

        return fields

    def update_features_form(self):
        return Playground.features_form(self)

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
                'full_text': ' | '.join([self.name or '', self.city or '', self.state or '', self.agency or '', self.owner or '', self.public_remarks or '']),
                'slug': self.slug,
                'display_name': self.display_name
            }
        }

        if self.latitude:
            # Convert to radians, scale up, convert to int and take the absolute value,
            # All in the service of storing as an accurate uint
            sdf['fields']['latitude'] = abs(int((self.latitude + app_config.CLOUD_SEARCH_DEG_OFFSET) * app_config.CLOUD_SEARCH_DEG_SCALE))
            sdf['fields']['longitude'] = abs(int((self.longitude + app_config.CLOUD_SEARCH_DEG_OFFSET) * app_config.CLOUD_SEARCH_DEG_SCALE))

        for feature in copytext.COPY.feature_list:
            slug = feature['key']

            if PlaygroundFeature.select().where(
                PlaygroundFeature.playground == self.id,
                PlaygroundFeature.slug == slug).count() > 0:
                sdf['fields']['feature_%s' % slug.replace('-', '_')] = 1
            else:
                sdf['fields']['feature_%s' % slug.replace('-', '_')] = 0

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
        Return a list of playgrounds near this one.
        See below for the implementation of the SQL distance algorithm.
        """
        if not self.latitude or not self.longitude:
            return []

        return list(Playground.raw('SELECT *, distance(?, ?, latitude, longitude) as distance FROM playground WHERE distance IS NOT NULL AND id <> ? AND active = 1 ORDER BY distance ASC LIMIT ?', self.latitude, self.longitude, self.id, n))

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


def display_field_name(field_name):
    """
    Convert any field or feature on a playground to
    a display-friendly version.
    """
    try:
        return getattr(Playground, field_name).verbose_name
    except AttributeError:
        feature = next(f for f in copytext.COPY.feature_list if f.key == field_name)

        return feature['term']


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
    """
    slug = CharField()
    playground = ForeignKeyField(Playground, cascade=False)

    class Meta:
        database = database

    @property
    def copy(self):
        for feature in copytext.COPY.feature_list:
            if feature['key'] == self.slug:
                return feature


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
    # For some reason, these are stored as unicode strings instead of datetime objects.
    # We're parsing them below in the get_timestamp() and get_est_time_formatted() functions.
    timestamp = DateTimeField()

    action = CharField()
    log = TextField()
    playground = ForeignKeyField(Playground, cascade=False)
    headers = TextField(null=True)
    cookies = TextField(null=True)
    revision_group = IntegerField()

    class Meta:
        database = database

    def get_timestamp(self):
        """
        Returns a UTC tz-aware datetime object.
        """
        # Strip timestamp to just the significant bits (no fractional secs or tz)
        timestamp = re.match('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', self.timestamp).group(1)
        timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        timestamp = timestamp.replace(tzinfo=pytz.utc)

        return timestamp

    def get_est_time_formatted(self):
        """
        Converts a UTC tz-aware datetime object to EST and outputs a string.
        """
        timestamp = self.get_timestamp()
        timestamp = timestamp.astimezone(pytz.timezone('US/Eastern'))
        return timestamp.strftime('%B %d, %Y %I:%M %p')

    def get_log(self):
        try:
            return json.loads(self.log)
        except:
            return None

    def get_headers(self):
        try:
            return json.loads(self.headers)
        except:
            return None

    def get_cookies(self):
        try:
            return json.loads(self.cookies)
        except:
            return None
