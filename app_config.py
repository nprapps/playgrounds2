#!/usr/bin/env python

"""
Project-wide application configuration.

DO NOT STORE SECRETS, PASSWORDS, ETC. IN THIS FILE.
They will be exposed to users. Use environment variables instead.
See get_secrets() below for a fast way to access them.
"""

import os

"""
NAMES
"""
# Project name used for display
PROJECT_NAME = 'Accessible Playgrounds'

# Project name used for paths on the filesystem and in urls
# Use dashes, not underscores
PROJECT_SLUG = 'playgrounds2'

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
PROJECT_DESCRIPTION = 'An opinionated project template for (mostly) server-less apps.'
SHARE_URL = 'http://%s/%s/' % (PRODUCTION_S3_BUCKETS[0], PROJECT_SLUG)


TWITTER = {
    'TEXT': PROJECT_NAME,
    'URL': SHARE_URL
}

FACEBOOK = {
    'TITLE': PROJECT_NAME,
    'URL': SHARE_URL,
    'DESCRIPTION': PROJECT_DESCRIPTION,
    'IMAGE_URL': '',
    'APP_ID': '138837436154588'
}

NPR_DFP = {
    'STORY_ID': '171421875',
    'TARGET': '\/news_politics;storyid=171421875'
}

"""
SERVICES
"""
GOOGLE_ANALYTICS_ID = 'UA-5828686-4'
DISQUS_SHORTNAME = 'npr-playgrounds2'

"""
Application specific
"""
DATA_GOOGLE_DOC_KEY = '0AlXMOHKxzQVRdGxsTklpUnBHV3NSRHFZaDVFWnQ5VVE'
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

ADMIN_EMAILS = [
    'playgrounds@npr.org',
    'jbowers@npr.org'
]

FEATURES = {
    'smooth-surface-throughout': {
        'name': 'Smooth surface throughout',
        'description': 'A surface that smooth enough for a wheelchair, and is resilient enough to cushion a fall.'
    },
    'ramps-to-play-components': {
        'name': 'Ramps to play components',
        'description': ' A path for a wheelchair to travel, not just to the playground, but within it as well.'
    },
    'transfer-stations-to-play-components': {
        'name': 'Transfer stations to play components',
        'description': ' Low platforms where those using wheelchairs can lift themselves out of them, onto playground equipment.'
    },
    'accessible-swing': {
        'name': 'Accessible swing',
        'description': 'Swings with features such as high backs and harnesses to assist special-needs children.'
    },
    'sound-play-components': {
        'name': 'Sound play components',
        'description': 'Outdoor devices that make sound or music, such as drums and marimbas.'
    },
    'sight-impaired-play-components': {
        'name': 'Sight-impaired play components',
        'description': ' Playground features that include Braille panels, interesting textures or fragrances.'
    },
    'safety-fence': {
        'name': 'Safety fence',
        'description': 'A fence enclosing the playground.'
    },
    'single-entrance': {
        'name': 'Single entrance',
        'description': 'Only one way in or out of the play area, to help parents and caregivers keep track of children.'
    }
}

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

        DISQUS_SHORTNAME = 'npr-playgrounds2'

    elif deployment_target == 'staging':
        S3_BUCKETS = STAGING_S3_BUCKETS
        SERVERS = STAGING_SERVERS
        DEBUG = True

        CLOUD_SEARCH_PROXY_BASE_URL = 'http://%s/%s' % (SERVERS[0], PROJECT_SLUG)
        S3_BASE_URL = 'http://%s/%s' % (S3_BUCKETS[0], PROJECT_SLUG)
        SERVER_BASE_URL = 'http://%s/%s' % (SERVERS[0], PROJECT_SLUG)

        DISQUS_SHORTNAME = 'npr-playgrounds2-staging'

    else:
        S3_BUCKETS = None
        SERVERS = None
        DEBUG = True

        CLOUD_SEARCH_PROXY_BASE_URL = 'http://127.0.0.1:8000'
        S3_BASE_URL = 'http://127.0.0.1:8000'
        SERVER_BASE_URL = 'http://127.0.0.1:8001/%s' % PROJECT_SLUG

        DISQUS_SHORTNAME = 'npr-playgrounds2-staging'

    DEPLOYMENT_TARGET = deployment_target

"""
Run automated configuration
"""
configure_targets(os.environ.get('DEPLOYMENT_TARGET', None))
