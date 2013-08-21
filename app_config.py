#!/usr/bin/env python

"""
Project-wide application configuration.

DO NOT STORE SECRETS, PASSWORDS, ETC. IN THIS FILE.
They will be exposed to users. Use environment variables instead.
See get_secrets() below for a fast way to access them.
"""

import os

from metros import metro_areas

"""
NAMES
"""
# Project name used for display
# When you change this, also change app_header_title in the copy spreadsheet
PROJECT_NAME = 'Playgrounds For Everyone'

# Project name used for paths on the filesystem and in urls
# Use dashes, not underscores
PROJECT_SLUG = 'playgrounds'

# The name of the repository containing the source
REPOSITORY_NAME = 'playgrounds2'

"""
DEPLOYMENT
"""
PRODUCTION_S3_BUCKETS = ['apps.npr.org', 'apps2.npr.org']
PRODUCTION_SERVERS = ['54.214.20.225']

STAGING_S3_BUCKETS = ['stage-apps.npr.org']
STAGING_SERVERS = ['54.214.20.232']

# Should code be deployed to the web/cron servers?
DEPLOY_TO_SERVERS = True

# Should the crontab file be installed on the servers?
# If True, DEPLOY_TO_SERVERS must also be True
DEPLOY_CRONTAB = True

# Should the service configurations be installed on the servers?
# If True, DEPLOY_TO_SERVERS must also be True
DEPLOY_SERVICES = True

# These variables will be set at runtime. See configure_targets() below
S3_BUCKETS = []
SERVERS = []
DEBUG = True
CLOUD_SEARCH_PROXY_BASE_URL = 'http://127.0.0.1:8000'
S3_BASE_URL = 'http://127.0.0.1:8000'
SERVER_BASE_URL = 'http://127.0.0.1:8001/%s' % PROJECT_SLUG

"""
COPY EDITING
"""
COPY_GOOGLE_DOC_KEY = '0AlXMOHKxzQVRdHR4bkdreFVEQWdCUjZpZEw0cVRCM1E'
COPY_URL = 'https://docs.google.com/spreadsheet/pub?key=%s&output=xls' % COPY_GOOGLE_DOC_KEY

"""
SHARING
"""
SHARE_URL = 'http://%s/%s/' % (PRODUCTION_S3_BUCKETS[0], PROJECT_SLUG)
PROJECT_DESCRIPTION = "Playgrounds For Everyone is NPR's community-edited guide to accessible playgrounds. Help us out!"

TWITTER = {
    'TEXT': PROJECT_DESCRIPTION,
    'URL': SHARE_URL,
    # Will be resized to 120x120, can't be larger than 1MB
    'IMAGE_URL': 'http://apps.npr.org/playgrounds/img/og-image-playgrounds.jpg'
}

FACEBOOK = {
    'TITLE': 'Playgrounds For Everyone',
    'URL': SHARE_URL,
    'DESCRIPTION': "Wood chips don't work for kids in wheelchairs. Some playgrounds are specially designed so that *all* kids can play alongside friends, siblings or any other child. NPR is building a guide to these playgrounds. You can help!",
    # Should be square. No documented restrictions on size
    'IMAGE_URL': TWITTER['IMAGE_URL'],
    'APP_ID': '138837436154588'
}

GOOGLE = {
    # Thumbnail image for Google News / Search.
    # No documented restrictions on resolution or size
    'IMAGE_URL': TWITTER['IMAGE_URL']
}

NPR_DFP = {
    'STORY_ID': '213812844',
    'TARGET': 'News_NPR_News_Investigations',
    'ENVIRONMENT': 'NPRTEST',
    'TESTSERVER': 'true'
}

"""
SERVICES
"""
GOOGLE_ANALYTICS_ID = 'UA-5828686-4'
DISQUS_SHORTNAME = 'npr-playgrounds2'

"""
Application specific
"""
DATA_GOOGLE_DOC_KEY = '0Antez86oOXPndGhEdGV6Qm9oMTQ0MFdVZTFnazRYaEE'
DATA_URL = 'https://docs.google.com/spreadsheet/pub?key=%s&single=true&gid=0&output=csv' % DATA_GOOGLE_DOC_KEY

MAPBOX_BASE_LAYER = 'npr.map-s5q5dags'
MAPBOX_BASE_LAYER_RETINA = 'npr.map-u1zkdj0e'

CLOUD_SEARCH_REGION = 'us-west-2'
CLOUD_SEARCH_INDEX_NAME = 'nprapps-playgrounds'
CLOUD_SEARCH_DOMAIN = 'search-nprapps-playgrounds-ujjvpbsloblpc625kcbhogeb3u.us-west-2.cloudsearch.amazonaws.com'
CLOUD_SEARCH_DOC_DOMAIN = 'doc-nprapps-playgrounds-ujjvpbsloblpc625kcbhogeb3u.us-west-2.cloudsearch.amazonaws.com'
CLOUD_SEARCH_DEFAULT_SEARCH_FIELD = ''  # empty string searches all text fields
CLOUD_SEARCH_DEG_OFFSET = 180
CLOUD_SEARCH_DEG_SCALE = 10000

RESULTS_DEFAULT_ZOOM = 14

ADMIN_EMAILS = [
    'playgrounds@npr.org',
    'jbowers@npr.org'
]

PUBLIC_FIELDS = [
    "name",
    "facility",
    "address",
    "city",
    "state",
    "zip_code",
    "agency",
    "owner",
    "public_remarks",
    "url",
    "id",
    "reverse_geocoded",
    "slug",
    "latitude",
    "longitude"
]

STATE_LIST = [
    'AL',
    'AK',
    'AZ',
    'AR',
    'CA',
    'CO',
    'CT',
    'DE',
    'DC',
    'FL',
    'GA',
    'HI',
    'ID',
    'IL',
    'IN',
    'IA',
    'KS',
    'KY',
    'LA',
    'ME',
    'MD',
    'MA',
    'MI',
    'MN',
    'MS',
    'MO',
    'MT',
    'NE',
    'NV',
    'NH',
    'NJ',
    'NM',
    'NY',
    'NC',
    'ND',
    'OH',
    'OK',
    'OR',
    'PA',
    'RI',
    'SC',
    'SD',
    'TN',
    'TX',
    'UT',
    'VT',
    'VA',
    'WA',
    'WV',
    'WI',
    'WY'
]

METRO_AREAS = metro_areas

"""
Utilities
"""
def get_secrets():
    """
    A method for accessing our secrets.
    """
    env_var_prefix = PROJECT_SLUG.replace('-', '')

    secrets = [
        # '%s_TUMBLR_APP_KEY' % env_var_prefix,
        # '%s_TUMBLR_OAUTH_TOKEN' % env_var_prefix,
        # '%s_TUMBLR_OAUTH_TOKEN_SECRET' % env_var_prefix,
        # '%s_TUMBLR_APP_SECRET' % env_var_prefix
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY'
    ]

    secrets_dict = {}

    for secret in secrets:
        # Saves the secret with the old name.
        secrets_dict[secret.replace('%s_' % env_var_prefix, '')] = os.environ.get(secret, None)

    return secrets_dict

def configure_targets(deployment_target):
    """
    Configure deployment targets. Abstracted so this can be
    overriden for rendering before deployment.
    """
    global S3_BUCKETS
    global SERVERS
    global DEBUG

    global CLOUD_SEARCH_PROXY_BASE_URL
    global S3_BASE_URL
    global SERVER_BASE_URL

    global DISQUS_SHORTNAME

    global DEPLOYMENT_TARGET

    if deployment_target == 'production':
        S3_BUCKETS = PRODUCTION_S3_BUCKETS
        SERVERS = PRODUCTION_SERVERS
        DEBUG = False

        CLOUD_SEARCH_PROXY_BASE_URL = 'http://%s/%s' % (SERVERS[0], PROJECT_SLUG)
        S3_BASE_URL = 'http://%s/%s' % (S3_BUCKETS[0], PROJECT_SLUG)
        SERVER_BASE_URL = 'http://%s/%s' % (SERVERS[0], PROJECT_SLUG)

        NPR_DFP['ENVIRONMENT'] = 'NPR'
        NPR_DFP['TESTSERVER'] = 'false'
        DISQUS_SHORTNAME = 'npr-playgrounds2'

    elif deployment_target == 'staging':
        S3_BUCKETS = STAGING_S3_BUCKETS
        SERVERS = STAGING_SERVERS
        DEBUG = True

        CLOUD_SEARCH_PROXY_BASE_URL = 'http://%s/%s' % (SERVERS[0], PROJECT_SLUG)
        S3_BASE_URL = 'http://%s/%s' % (S3_BUCKETS[0], PROJECT_SLUG)
        SERVER_BASE_URL = 'http://%s/%s' % (SERVERS[0], PROJECT_SLUG)

        NPR_DFP['ENVIRONMENT'] = 'NPRTEST'
        NPR_DFP['TESTSERVER'] = 'true'
        DISQUS_SHORTNAME = 'npr-playgrounds2-staging'

    else:
        S3_BUCKETS = None
        SERVERS = None
        DEBUG = True

        CLOUD_SEARCH_PROXY_BASE_URL = 'http://127.0.0.1:8000'
        S3_BASE_URL = 'http://127.0.0.1:8000'
        SERVER_BASE_URL = 'http://127.0.0.1:8001/%s' % PROJECT_SLUG

        NPR_DFP['ENVIRONMENT'] = 'NPRTEST'
        NPR_DFP['TESTSERVER'] = 'true'
        DISQUS_SHORTNAME = 'npr-playgrounds2-staging'

    DEPLOYMENT_TARGET = deployment_target

"""
Run automated configuration
"""
configure_targets(os.environ.get('DEPLOYMENT_TARGET', None))
