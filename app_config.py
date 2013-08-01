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
PROJECT_NAME = 'Where All Kids Play'

# Project name used for paths on the filesystem and in urls
# Use dashes, not underscores
PROJECT_SLUG = 'where-all-kids-play'

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
    'STORY_ID': '203618536',
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

METRO_AREAS = [
    {
        "name": "New York-Newark-Jersey City, NY-NJ-PA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "New York, NY",
    },
    {
        "name": "Los Angeles-Long Beach-Anaheim, CA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Los Angeles, CA",
    },
    {
        "name": "Chicago-Naperville-Elgin, IL-IN-WI",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Chicago, IL",
    },
    {
        "name": "Dallas-Fort Worth-Arlington, TX",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Arlington, TX",
    },
    {
        "name": "Houston-The Woodlands-Sugar Land, TX",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Houston, TX",
    },
    {
        "name": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Philadelphia, PA",
    },
    {
        "name": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
        "zip_codes": [20001, 20005, 20006, 20002, 20003, 20004, 20007],
        "playground_count": 0,
        "search_name": "Washington, DC",
    },
    {
        "name": "Miami-Fort Lauderdale-West Palm Beach, FL",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Miami, FL",
    },
    {
        "name": "Atlanta-Sandy Springs-Roswell, GA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Atlanta, GA",
    },
    {
        "name": "Boston-Cambridge-Newton, MA-NH",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Boston, MA",
    },
    {
        "name": "San Francisco-Oakland-Fremont, CA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "San Francisco, CA",
    },
    {
        "name": "Riverside-San Bernardino-Ontario, CA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Riverside, CA",
    },
    {
        "name": "Phoenix-Mesa-Scottsdale, AZ",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Phoenix, AZ",
    },
    {
        "name": "Detroit-Warren-Dearborn, MI",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Detroit, MI",
    },
    {
        "name": "Seattle-Tacoma-Bellevue, WA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Seattle, WA",
    },
    {
        "name": "Minneapolis-St. Paul-Bloomington, MN-WI",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Minneapolis, MN",
    },
    {
        "name": "San Diego-Carlsbad, CA",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "San Diego, CA",
    },
    {
        "name": "Tampa-St. Petersburg-Clearwater, FL",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Tampa, FL",
    },
    {
        "name": "St. Louis, MO-IL",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "St. Louis, MO",
    },
    {
        "name": "Baltimore-Columbia-Towson, MD",
        "zip_codes": [],
        "playground_count": 0,
        "search_name": "Baltimore, MD",
    },
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

        NPR_DFP.ENVIRONMENT = 'NPR'
        NPR_DFP.TESTSERVER = 'false'
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
