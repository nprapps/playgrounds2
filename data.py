#!/usr/bin/env python

import datetime
import json
import math
import time
from sets import Set

from csvkit import CSVKitDictReader
from jinja2 import Template
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
                    <label class="checkbox">
                    <input type="checkbox" name="%s" checked="checked">
                        &nbsp;%s
                    </label>""" % (f.replace(' ', '-').lower(), f))
            else:
                fields.append("""
                    <label class="checkbox">
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
    revision_group = IntegerField()

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


def prepare_email(revision_group=None):
    if not revision_group:
        revision_group = 1371164033.0
    revisions = Revision.select().where(Revision.revision_group == int(revision_group))
    context = {}
    context['total_revisions'] = revisions.count()
    context['playgrounds'] = []

    updated_playgrounds = Set([])

    for revision in revisions:
        updated_playgrounds.add(revision.playground.id)

    for playground_id in updated_playgrounds:
        p = Playground.get(id=playground_id)
        playground_dict = p.__dict__['_data']
        playground_dict['site_url'] = 'http://127.0.0.1:8000/playground/%s.html' % playground_id
        playground_dict['revisions'] = []
        for revision in revisions:
            if revision.playground.id == playground_id:
                revision_dict = {}
                revision_dict['revision_group'] = revision_group
                revision_dict['fields'] = revision.get_log()
                playground_dict['revisions'].append(revision_dict)
        context['playgrounds'].append(playground_dict)

    with open('templates/_email.html', 'rb') as read_template:
        payload = Template(read_template.read())

    return payload.render(**context)

def parse_updates():

    # The revision_group is a single pass of this cron job.
    # This is a grouping of all updates made in one run of the function.
    revision_group = time.mktime((datetime.datetime.utcnow()).timetuple())

    # Set up a blank list of updates.
    updates = []

    # Open the updates file and load the JSON as the updates list.
    with open('updates-in-progress.json', 'r') as jsonfile:
        updates = json.loads(jsonfile.read())

    # Set up a blank list of updated playgrounds.
    updated_playgrounds = []

    # Okay, the fun part.
    # Loop through the updates.
    for record in updates:

        # First, capture the old data from this playground. 
        old_data = Playground.get(id=record['playground']['id']).__dict__['_data']

        # This is an intermediate data store for this record.
        record_dict = {}

        # Loop through each of the key/value pairs in the playground record.
        for key, value in record['playground'].items():

            # Ignore some keys because they aren't really what we want to update.
            if key not in ['id', 'timestamp', 'features']:

                # If the value is blank, make it null.
                # Life is too short for many different kinds of emptyness.
                if value == u'':
                    value = None

                # Update the record_dict with our new key/value pair.
                record_dict[key] = value

        # Run the update query against this playground.
        # Pushes any updates in the record_dict to the model.
        Playground.update(**record_dict).where(Playground.id == int(record['playground']['id'])).execute()

        # Add this playground to the updated_playgrounds list.
        updated_playgrounds.append(record['playground']['id'])

        # Set up the list of old features.
        # We're going to remove them all.
        # We'll re-add anything that stuck around.
        old_features = []

        # Append the old features to the list.
        for feature in PlaygroundFeature.select().where(PlaygroundFeature.playground == record['playground']['id']):
            old_features.append(feature.slug)

        # Delete any features attached to this playground.
        PlaygroundFeature.delete().where(PlaygroundFeature.playground == record['playground']['id']).execute()

        # Check to see if we have any incoming features from the updates.json.
        # If we don't, set up an empty list.
        try:
            features = record['playground']['features']
        except KeyError:
            features = []

        # If we have an empty list, give up and go home.
        # Otherwise, continue to the promised land.
        if len(features) > 0:

            # Loop over the features list.
            for feature in features:

                    # Loop over the entire set of features from app_config.
                    # This makes sure people don't submit random features.
                    # And it lets us look up by slug, which is what we're kinda doing.
                    for f, slug in app_config.FEATURE_LIST:

                        # If this feature matches the slug of something from the app_config
                        # feature list, attach it to the playground.
                        if feature == slug:

                            # Get the playground object.
                            p = Playground.get(id=record['playground']['id'])

                            # Create a new playground feature object.
                            pf = PlaygroundFeature(slug=slug, name=f, playground=p)

                            # Save it like it's hot.
                            pf.save()

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
            for f, slug in app_config.FEATURE_LIST:

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

        Revision(
            playground=Playground.get(id=record['playground']['id']),
            timestamp=int(record['playground']['timestamp']),
            log=json.dumps(revisions),
            headers=json.dumps(record['request']['headers']),
            cookies=json.dumps(record['request']['cookies']),
            revision_group=revision_group
        ).save()

    return (updated_playgrounds, revision_group)
