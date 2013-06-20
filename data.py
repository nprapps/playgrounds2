#!/usr/bin/env python

import datetime
import json
import math
import re
import time
from sets import Set

import boto
from boto import cloudsearch
from boto.cloudsearch.domain import Domain
from boto.s3.bucket import Bucket
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from csvkit import CSVKitDictReader
from geopy import geocoders
from jinja2 import Template
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase

import app_config

database = SqliteExtDatabase('playgrounds.db')


US_STATES = (('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('DC', 'District of Columbia'), ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'))


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

    if lat1 == lat2 and lng1 == lng2:
        return 0

    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    return 3958.761 * math.acos(math.sin(lat1_rad) * math.sin(lat2_rad) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lng2_rad - lng1_rad))


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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slugify()
        # if (not self.latitude or self.longitude):
        #     self.geocode()

        super(Playground, self).save(*args, **kwargs)

    def remove_from_s3(self):
        """
        Removes file for this model instance from S3
        """

        # fetch secrets from app_config
        secrets = app_config.get_secrets()

        # connect to S3
        conn = S3Connection(secrets['AWS_ACCESS_KEY_ID'],secrets['AWS_SECRET_ACCESS_KEY'])

        # loop over buckets, we have more than one, and remove this playground
        for bucket in app_config.S3_BUCKETS:
            b = Bucket(conn, bucket)
            k = Key(b)
            k.key = '/playground/%s.html' % (self.slug)
            b.delete_key(k)

    def remove_from_search_index(self):
        """
        Removes a playground from search index
        """

        # Set up a cloudsearch connection.
        conn = cloudsearch.connect_to_region(app_config.CLOUD_SEARCH_REGION)

        # Loop over our domains and find the one with the matching document  endpoint.
        for domain in conn.describe_domains():
            if domain['doc_service']['endpoint'] == app_config.CLOUD_SEARCH_DOC_DOMAIN:
                d = domain

        # Make an object of our domain.
        domain = Domain(conn, d)

        # Domain objects have a get_document_service() function, which we need.
        doc_service = domain.get_document_service()

        # Get a timestamp.
        now = int(time.mktime(datetime.datetime.utcnow().timetuple()))

        # Call the delete function. Pass the constructed id and the timestamp.
        # Objects are only removed if this timestamp is higher than the one in the index.
        doc_service.delete('%s_%s' % (app_config.DEPLOYMENT_TARGET, self.id), now)

        # Commit it!
        doc_service.commit()

    def deactivate(self):
        """
        Deactivates a model instance by calling deletes from S3 and Cloudsearch
        """

        # Deactivate playgrounds flagged for removal and commit it to the database
        self.active = False
        self.save()

        # Reach into the bowels of S3 and Cloudsearch
        self.remove_from_s3()
        self.remove_from_search_index()

    @property
    def features(self):
        """
        Return an iterable containing features.
        Empty list if none.
        """
        features = []
        for feature in PlaygroundFeature.select().where(PlaygroundFeature.playground == self.id):
            features.append(feature.__dict__['_data'])
        return features

    def slugify(self):
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
                'name': self.name,
                'city': self.city,
                'state': self.state,
                'zip_code': self.zip_code,
                'facility': self.facility,
                'agency': self.agency,
                'owner': self.owner,
                'owner_type': self.owner_type,
                'public_remarks': self.public_remarks,
                'full_text': ' | '.join([self.name, self.city, self.state, self.agency, self.owner, self.public_remarks]),
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


def get_active_playgrounds():
    """
    A function which acts like a Django model manger.
    Returns only active playgrounds.
    Can chain .where() clauses against this, e.g.,
    all active playgrounds in NY:

        get_active_playgrounds().where(Playground.state == 'NY')
    """
    return Playground.select().where(Playground.active == True)


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
    Playground.create_table()
    PlaygroundFeature.create_table()
    Revision.create_table()

def load_playgrounds(path='data/playgrounds.csv'):
    """
    Load playground data from the CSV into sqlite.
    """
    with open(path) as f:
        rows = CSVKitDictReader(f)

        for row in rows:
            if row['Duplicate'] == 'TRUE':
                #print 'Skipping duplicate: %s' % row['NAME']
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


def prepare_email(revision_group):
    revisions = Revision.select().where(Revision.revision_group == int(revision_group))
    context = {}
    context['total_revisions'] = revisions.count()
    context['playgrounds'] = []

    updated_playgrounds = Set([])

    for revision in revisions:
        updated_playgrounds.add(revision.playground.slug)

    for playground_slug in updated_playgrounds:
        p = Playground.get(slug=playground_slug)
        playground_dict = p.__dict__['_data']
        playground_dict['site_url'] = 'http://%s/playground/%s.html' % (app_config.S3_BASE_URL, playground_slug)
        playground_dict['revisions'] = []
        for revision in revisions:
            if revision.playground.id == p.id:
                revision_dict = {}
                revision_dict['revision_group'] = revision_group
                revision_dict['fields'] = revision.get_log()
                playground_dict['revisions'].append(revision_dict)
        context['playgrounds'].append(playground_dict)

    with open('templates/_email.html', 'rb') as read_template:
        payload = Template(read_template.read())

    return payload.render(**context)

def process_changes(path='changes-in-process.json'):
    """
    Iterate over changes.json and process it's contents.
    """
    revision_group = time.mktime((datetime.datetime.utcnow()).timetuple())

    with open(path) as f:
        changes = json.load(f)

    # A list of slugs of new or updated playgrounds
    changed_playgrounds = []

    for record in changes:
        if record['action'] == 'update':
            playground, revisions = process_update(record)
            changed_playgrounds.append(playground.slug)
        elif record['action'] == 'insert':
            playground, revisions = process_insert(record)
            changed_playgrounds.append(playground.slug)
        elif record['action'] == 'delete':
            #playground, revisions = process_delete(record)
            pass

        Revision.create(
            timestamp=int(record['timestamp']),
            action=record['action'],
            playground=playground,
            log=json.dumps(revisions),
            headers=json.dumps(record['request']['headers']),
            cookies=json.dumps(record['request']['cookies']),
            revision_group=revision_group
        )

    return (changed_playgrounds, revision_group)


def process_update(record):
    """
    Process a single update record from changes.json.
    """
    playground_id = record['playground']['id']

    # First, capture the old data from this playground.
    old_data = Playground.get(id=playground_id).__dict__['_data']

    # This is an intermediate data store for this record.
    record_dict = {}

    # Loop through each of the key/value pairs in the playground record.
    for key, value in record['playground'].items():

        # Ignore some keys because they aren't really what we want to update.
        if key not in ['id', 'features']:

            # If the value is blank, make it null.
            # Life is too short for many different kinds of emptyness.
            if value == u'':
                value = None

            # Update the record_dict with our new key/value pair.
            record_dict[key] = value

    # Run the update query against this playground.
    # Pushes any updates in the record_dict to the model.
    playground = Playground.get(id=playground_id)

    if (record_dict):
        playground.update(**record_dict).execute()

    # Set up the list of old features.
    # We're going to remove them all.
    # We'll re-add anything that stuck around.
    old_features = []

    # Append the old features to the list.
    for feature in PlaygroundFeature.select().where(PlaygroundFeature.playground == playground_id):
        old_features.append(feature.slug)

    # Delete any features attached to this playground.
    PlaygroundFeature.delete().where(PlaygroundFeature.playground == playground_id).execute()

    # Check to see if we have any incoming features.
    try:
        features = record['playground']['features']
    except KeyError:
        features = []

    for slug in features:
        PlaygroundFeature.create(
            slug=slug,
            playground=playground
        )

    # Now, let's set up some revisions.
    # Create a list of revisions to apply.
    revisions = []

    # Our old data was captured up top. It's called old_data.
    # This is the new data. It's just the record_dict from above.
    new_data = record_dict

    # Loop over the key/value pairs in the new data we have.
    for key, value in new_data.items():

        # Fix the variety of None that we bother maintaining.
        if value is None:
            new_data[key] = ''

        # Now, if the old data and the new data don't match, let's make a revision.
        if old_data[key] != new_data[key]:

            # Set up an intermediate data structure for the revision.
            revision_dict = {}

            # Set up the data for this revision.
            revision_dict['field'] = key
            revision_dict['from'] = old_data[key]
            revision_dict['to'] = new_data[key]

            # Append it to the revisions list.
            revisions.append(revision_dict)

    # Let's get started on features.
    # First, let's figure out the new features coming from the Web.
    try:
        # If there are any new features, create a list for them.
        new_features = record['playground']['features']
    except:
        # Otherwise, empty list.
        new_features = []

    # First case: If the list of old and new features is identical, don't do anything.
    if old_features != new_features:

        # So there's a difference between the old and new feature lists.
        # Since the Web can both add new features and remove old features,
        # we have to prepare for each path.
        # First, let's loop over the list of features that are available.
        for slug in app_config.FEATURES.keys():

            # If the slug is in the old feature set, let's check it against the new.
            if slug in old_features:

                # If it's not in the new feature set but IS in the old feature set,
                # let's append a revision taking it from 1 to 0.
                if slug not in new_features:
                    revisions.append({"field": slug, "from": 1, "to": 0})

            # Similarly, if the slug in the new feature set, let's check it agains the old.
            if slug in new_features:

                # If it's not in the old_feature set but IS in the new feature set,
                # let's append a revision taking it from 0 to 1.
                if slug not in old_features:
                    revisions.append({"field": slug, "from": 0, "to": 1})

    return playground, revisions

def process_insert(record):
    """
    Process a single insert record from changes.json.
    """
    playground = Playground()

    record_dict = {}

    # Loop through each of the key/value pairs in the playground record.
    for key, value in record['playground'].items():

        # Ignore some keys because they aren't really what we want to update.
        if key not in ['id', 'features']:

            # If the value is blank, make it null.
            # Life is too short for many different kinds of emptyness.
            if value == u'':
                value = None

            # Update the record_dict with our new key/value pair.
            record_dict[key] = value
            setattr(playground, key, value)

    playground.save()

    # Create a list of revisions that were applied.
    revisions = []

    # Our old data was captured up top. It's called old_data.
    # This is the new data. It's just the record_dict from above.
    new_data = record_dict

    # Loop over the key/value pairs in the new data we have.
    for key, value in new_data.items():

        # Fix the variety of None that we bother maintaining.
        if value is None:
            new_data[key] = ''

        # Set up an intermediate data structure for the revision.
        revision_dict = {}

        # Set up the data for this revision.
        revision_dict['field'] = key
        revision_dict['from'] = ''
        revision_dict['to'] = new_data[key]

        # Append it to the revisions list.
        revisions.append(revision_dict)

    # Check to see if we have any incoming features.
    try:
        features = record['playground']['features']
    except KeyError:
        features = []

    for feature in features:
        PlaygroundFeature.create(
            slug=slug,
            playground=playground
        )

        revisions.append({'field': slug, 'from': '0', 'to': '1'})

    return (playground, revisions)

def process_delete(record):
    # TKTK
    pass
