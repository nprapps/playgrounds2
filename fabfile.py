#!/usr/bin/env python

import datetime
from glob import glob
import json
import os
import time

import boto.cloudsearch
import boto.ses
from fabric.api import *
from jinja2 import Template
import requests
import pytz

import app
import app_config
import copytext
import data
from etc import github
import models


"""
Base configuration
"""
env.project_slug = app_config.PROJECT_SLUG
env.repository_name = app_config.REPOSITORY_NAME

env.deploy_to_servers = app_config.DEPLOY_TO_SERVERS
env.deploy_crontab = app_config.DEPLOY_CRONTAB
env.deploy_services = app_config.DEPLOY_SERVICES

env.repo_url = 'git@github.com:nprapps/%(repository_name)s.git' % env
env.alt_repo_url = None  # 'git@bitbucket.org:nprapps/%(repository_name)s.git' % env
env.user = 'ubuntu'
env.python = 'python2.7'
env.path = '/home/%(user)s/apps/%(project_slug)s' % env
env.repo_path = '%(path)s/repository' % env
env.virtualenv_path = '%(path)s/virtualenv' % env
env.forward_agent = True

# Services are the server-side services we want to enable and configure.
# A three-tuple following this format:
# (service name, service deployment path, service config file extension)
SERVICES = [
    ('app', '%(repo_path)s/' % env, 'ini'),
    ('uwsgi', '/etc/init/', 'conf'),
    ('nginx', '/etc/nginx/locations-enabled/', 'conf'),
]

"""
Environments

Changing environment requires a full-stack test.
An environment points to both a server and an S3
bucket.
"""
def production():
    env.settings = 'production'
    env.s3_buckets = app_config.PRODUCTION_S3_BUCKETS
    env.hosts = app_config.PRODUCTION_SERVERS

def staging():
    env.settings = 'staging'
    env.s3_buckets = app_config.STAGING_S3_BUCKETS
    env.hosts = app_config.STAGING_SERVERS

"""
Branches

Changing branches requires deploying that branch to a host.
"""
def stable():
    """
    Work on stable branch.
    """
    env.branch = 'stable'

def master():
    """
    Work on development branch.
    """
    env.branch = 'master'

def branch(branch_name):
    """
    Work on any specified branch.
    """
    env.branch = branch_name

"""
Template-specific functions

Changing the template functions should produce output
with fab render without any exceptions. Any file used
by the site templates should be rendered by fab render.
"""
def less():
    """
    Render LESS files to CSS.
    """
    for path in glob('less/*.less'):
        filename = os.path.split(path)[-1]
        name = os.path.splitext(filename)[0]
        out_path = 'www/css/%s.less.css' % name

        local('node_modules/.bin/lessc %s %s' % (path, out_path))

def jst():
    """
    Render Underscore templates to a JST package.
    """
    local('node_modules/.bin/jst --template underscore jst www/js/templates.js')

def update_copy():
    """
    Fetches the latest Google Doc and updates local JSON.
    """
    local('curl -o data/copy.xls "%s"' % app_config.COPY_URL)

def app_config_js():
    """
    Render app_config.js to file.
    """
    from app import _app_config_js

    response = _app_config_js()
    js = response[0]

    with open('www/js/app_config.js', 'w') as f:
        f.write(js)

def copy_text_js():
    """
    Render copy_text messages to a js file.
    """
    copy = {}

    for message in ['editing_thanks', 'creating_thanks', 'deleting_thanks']:
        copy[message] = unicode(getattr(copytext.Copy().content, message))

    with open('www/js/copy_text.js', 'w') as f:
        f.write('window.COPYTEXT = %s' % json.dumps(copy))

def render():
    """
    Render HTML templates and compile assets.
    """
    from flask import g

    update_copy()
    less()
    jst()

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    app_config_js()
    copy_text_js()

    compiled_includes = []

    for rule in app.app.url_map.iter_rules():
        rule_string = rule.rule
        name = rule.endpoint

        if name == 'static' or name.startswith('_'):
            print 'Skipping %s' % name
            continue

        if rule_string.endswith('/'):
            filename = 'www' + rule_string + 'index.html'
        elif rule_string.endswith('.html') or rule_string.endswith('.xml'):
            filename = 'www' + rule_string
        else:
            print 'Skipping %s' % name
            continue

        dirname = os.path.dirname(filename)

        if not (os.path.exists(dirname)):
            os.makedirs(dirname)

        print 'Rendering %s' % (filename)

        with app.app.test_request_context(path=rule_string):
            g.compile_includes = True
            g.compiled_includes = compiled_includes

            view = app.__dict__[name]
            content = view()

            if isinstance(content, tuple):
                content = content[0]

            compiled_includes = g.compiled_includes

        with open(filename, 'w') as f:
            f.write(content.encode('utf-8'))

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

def render_playgrounds(playgrounds=None):
    """
    Render the playgrounds pages.
    """
    from flask import g, url_for

    update_copy()
    less()
    jst()

    if not playgrounds:
        playgrounds = models.Playground.select()

    slugs = [p.slug for p in playgrounds]

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    app_config_js()
    copy_text_js()

    compiled_includes = []

    for slug in slugs:
        # Silly fix because url_for require a context
        with app.app.test_request_context():
            path = url_for('_playground', playground_slug=slug)

        with app.app.test_request_context(path=path):
            print 'Rendering %s' % path

            g.compile_includes = True
            g.compiled_includes = compiled_includes

            view = app.__dict__['_playground']
            content = view(slug)

            compiled_includes = g.compiled_includes

        path = '.playgrounds_html%s' % path

        # Ensure path exists
        head = os.path.split(path)[0]

        try:
            os.makedirs(head)
        except OSError:
            pass

        with open(path, 'w') as f:
            f.write(content.encode('utf-8'))

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

def tests():
    """
    Run Python unit tests.
    """
    with settings(warn_only=True):
        local('mv playgrounds.db playgrounds.db.bak')
        local('mv data/changes.json data/changes.json.bak')

        local('nosetests --with-coverage --cover-html --cover-html-dir=.coverage-html --cover-package=data,public_app')

        local('mv playgrounds.db.bak playgrounds.db')
        local('mv data/changes.json.bak data/changes.json')

"""
Setup

Changing setup commands requires a test deployment to a server.
Setup will create directories, install requirements and set up logs.
It may also need to set up Web services.
"""
def setup():
    """
    Setup servers for deployment.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])

    setup_directories()
    setup_virtualenv()
    clone_repo()
    checkout_latest()
    install_requirements()

    if env['deploy_services']:
        deploy_confs()

def setup_directories():
    """
    Create server directories.
    """
    require('settings', provided_by=[production, staging])

    run('mkdir -p %(path)s' % env)
    run('mkdir -p /var/www/uploads/%(project_slug)s' % env)

def setup_virtualenv():
    """
    Setup a server virtualenv.
    """
    require('settings', provided_by=[production, staging])

    run('virtualenv -p %(python)s --no-site-packages %(virtualenv_path)s' % env)
    run('source %(virtualenv_path)s/bin/activate' % env)

def clone_repo():
    """
    Clone the source repository.
    """
    require('settings', provided_by=[production, staging])

    run('git clone %(repo_url)s %(repo_path)s' % env)

    if env.get('alt_repo_url', None):
        run('git remote add bitbucket %(alt_repo_url)s' % env)

def checkout_latest(remote='origin'):
    """
    Checkout the latest source.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])

    env.remote = remote

    run('cd %(repo_path)s; git fetch %(remote)s' % env)
    run('cd %(repo_path)s; git checkout %(branch)s; git pull %(remote)s %(branch)s' % env)

def install_requirements():
    """
    Install the latest requirements.
    """
    require('settings', provided_by=[production, staging])

    run('%(virtualenv_path)s/bin/pip install -U -r %(repo_path)s/requirements.txt' % env)

def install_crontab():
    """
    Install cron jobs script into cron.d.
    """
    require('settings', provided_by=[production, staging])

    sudo('cp %(repo_path)s/crontab /etc/cron.d/%(project_slug)s' % env)

def uninstall_crontab():
    """
    Remove a previously install cron jobs script from cron.d
    """
    require('settings', provided_by=[production, staging])

    sudo('rm /etc/cron.d/%(project_slug)s' % env)

def bootstrap_issues():
    """
    Bootstraps Github issues with default configuration.
    """
    auth = github.get_auth()
    github.delete_existing_labels(auth)
    github.create_labels(auth)
    github.create_tickets(auth)

"""
Deployment

Changes to deployment requires a full-stack test. Deployment
has two primary functions: Pushing flat files to S3 and deploying
code to a remote server if required.
"""
def _deploy_to_s3(src='gzip'):
    """
    Deploy the gzipped stuff to S3.
    """
    s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --guess-mime-type --recursive --exclude-from gzip_types.txt sync %s/ %s'
    s3cmd_gzip = 's3cmd -P --add-header=Cache-Control:max-age=5 --add-header=Content-encoding:gzip --guess-mime-type --recursive --exclude "*" --include-from gzip_types.txt sync %s/ %s'

    for bucket in env.s3_buckets:
        env.s3_bucket = bucket
        local(s3cmd % (src, 's3://%(s3_bucket)s/%(project_slug)s/' % env))
        local(s3cmd_gzip % (src, 's3://%(s3_bucket)s/%(project_slug)s/' % env))

def _gzip(src='www', dst='gzip'):
    """
    Gzips everything in www and puts it all in gzip
    """
    local('python gzip_www.py %s %s' % (src, dst))
    local('rm -rf %s/live-data' % dst)


def render_confs():
    """
    Renders server configurations.
    """
    require('settings', provided_by=[production, staging])

    with settings(warn_only=True):
        local('mkdir confs/rendered')

    context = app_config.get_secrets()
    context['PROJECT_SLUG'] = app_config.PROJECT_SLUG
    context['CLOUD_SEARCH_DOMAIN'] = app_config.CLOUD_SEARCH_DOMAIN
    context['PROJECT_NAME'] = app_config.PROJECT_NAME
    context['DEPLOYMENT_TARGET'] = env.settings
    context['CONFIG_NAME'] = env.project_slug.replace('-', '').upper()

    for service, remote_path, extension in SERVICES:
        file_path = 'confs/rendered/%s.%s.%s' % (app_config.PROJECT_SLUG, service, extension)

        with open('confs/%s.%s' % (service, extension),  'r') as read_template:

            with open(file_path, 'wb') as write_template:
                payload = Template(read_template.read())
                write_template.write(payload.render(**context))


def deploy_confs():
    """
    Deploys rendered server configurations to the specified server.
    This will reload nginx and the appropriate uwsgi config.
    """
    require('settings', provided_by=[production, staging])

    render_confs()

    with settings(warn_only=True):
        run('touch /tmp/%s.sock' % app_config.PROJECT_SLUG)
        sudo('chmod 777 /tmp/%s.sock' % app_config.PROJECT_SLUG)

        for service, remote_path, extension in SERVICES:
            service_name = '%s.%s' % (app_config.PROJECT_SLUG, service)
            file_name = '%s.%s' % (service_name, extension)
            local_path = 'confs/rendered/%s' % file_name
            remote_path = '%s%s' % (remote_path, file_name)

            a = local('md5 -q %s' % local_path, capture=True)
            b = run('md5sum %s' % remote_path).split()[0]

            if a != b:
                put(local_path, remote_path, use_sudo=True)

                if service == 'nginx':
                    sudo('service nginx reload')
                else:
                    sudo('initctl reload-configuration')
                    sudo('service %s restart' % service_name)


def deploy(remote='origin'):
    """
    Deploy the latest app to S3 and, if configured, to our servers.
    """
    require('settings', provided_by=[production, staging])

    if env.get('deploy_to_servers', False):
        require('branch', provided_by=[stable, master, branch])

    if (env.settings == 'production' and env.branch != 'stable'):
        _confirm("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env)

    render()
    _gzip()
    _deploy_to_s3()

    if env['deploy_to_servers']:
        checkout_latest(remote)

        if env['deploy_crontab']:
            install_crontab()

        if env['deploy_services']:
            deploy_confs()

def deploy_playgrounds():
    require('settings', provided_by=[production, staging])

    if (env.settings == 'production' and env.branch != 'stable'):
        _confirm("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env)

    render_playgrounds()
    _gzip('.playgrounds_html', '.playgrounds_gzip')
    _deploy_to_s3('.playgrounds_gzip')


"""
Application specific
"""
def _send_email(addresses, payload):
    connection = boto.ses.connect_to_region('us-east-1')
    connection.send_email(
        'NPR News Apps <nprapps@npr.org>',
        'Playgrounds: %s' % (datetime.datetime.now(pytz.utc).replace(tzinfo=pytz.utc).strftime('%m/%d')),
        None,
        addresses,
        html_body=payload,
        format='html')

def send_test_email():
    payload = """
    <html>
        <head></head>
        <body>
            <h1>Howdy!</h1>
            <p><a href="http://www.npr.org/">This is a test</a> email.</p>
            <p><a href="http://www.npr.org/">Delete</a></p>
        </body>
    </html>
    """
    addresses = app_config.ADMIN_EMAILS
    _send_email(addresses, payload)

def send_fake_revision_email(revision_group=2):
    payload = app._prepare_email(revision_group)
    addresses = app_config.ADMIN_EMAILS
    _send_email(addresses, payload)

def send_revision_email(revision_group):
    payload = app._prepare_email(revision_group)
    addresses = app_config.ADMIN_EMAILS
    _send_email(addresses, payload)

def download_data():
    """
    Download the latest playgrounds data CSV.
    """
    local('curl -o data/playgrounds.csv "%s"' % app_config.DATA_URL)

def load_data():
    """
    Clear and reload playground data from CSV into sqlite.
    """
    models.delete_tables()
    models.create_tables()
    data.load_playgrounds()

def local_bootstrap():
    """
    Get and load all data required to make the app run.
    """
    update_copy()
    download_data()
    load_data()

def bootstrap():
    require('settings', provided_by=[production, staging])
    local_bootstrap()
    put(local_path='playgrounds.db', remote_path='%(repo_path)s/playgrounds.db' % env)

def process_changes():
    """
    Parse any updates waiting to be processed, rerender playgrounds and send notification emails.
    """
    require('settings', provided_by=[production, staging])

    local('cp playgrounds.db data/%s-playgrounds.db' % time.mktime((datetime.datetime.now(pytz.utc)).timetuple()))
    local('cp data/changes.json changes-in-progress.json && rm -f data/changes.json')
    changed_playgrounds, revision_group = data.process_changes()
    render_playgrounds(changed_playgrounds)
    update_search_index(changed_playgrounds)
    send_revision_email(revision_group)
    local('rm -f changes-in-progress.json')

def update_search_index(playgrounds=None):
    """
    Batch upload playgrounds to CloudSearch as SDF.
    """
    require('settings', provided_by=[production, staging])

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    if not playgrounds:
        playgrounds = models.Playground.select()

    print 'Generating SDF batch...'
    sdf = [playground.sdf() for playground in playgrounds]
    payload = json.dumps(sdf)

    if len(payload) > 5000 * 1024:
        print 'Exceeded 5MB limit for SDF uploads!'
        return

    print 'Uploading to CloudSearch...'
    response = requests.post('http://%s/2011-02-01/documents/batch' % app_config.CLOUD_SEARCH_DOC_DOMAIN, data=payload, headers={ 'Content-Type': 'application/json' })

    print response.status_code
    print response.text

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

def clear_search_index():
    require('settings', provided_by=[production, staging])

    _confirm("You are about to delete the %(settings)s search index for this project.\nDo you know what you're doing?" % env)

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    print 'Generating SDF batch...'
    sdf = [playground.delete_sdf() for playground in models.Playground.select()]
    payload = json.dumps(sdf)

    if len(payload) > 5000 * 1024:
        print 'Exceeded 5MB limit for SDF uploads!'
        return

    print 'Uploading to CloudSearch...'
    response = requests.post('http://%s/2011-02-01/documents/batch' % app_config.CLOUD_SEARCH_DOC_DOMAIN, data=payload, headers={ 'Content-Type': 'application/json' })

    print response.status_code
    print response.text

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

def set_default_search_field():
    """
    Use Boto to configure CloudSearch with the default search field.

    There is no UI for this in the management console.
    """
    cloudsearch = boto.cloudsearch.connect_to_region(app_config.CLOUD_SEARCH_REGION)
    cloudsearch.update_default_search_field(app_config.CLOUD_SEARCH_INDEX_NAME, app_config.CLOUD_SEARCH_DEFAULT_SEARCH_FIELD)

def create_test_revisions():
    """
    Create a series of dummy revisions for local styling and such.

    Doesn't actually modify the playground instance.
    """
    playground = models.Playground.get(id=1)
    playground2 = models.Playground.get(id=2)

    now = datetime.datetime.now(pytz.utc)

    models.Revision.create(
        timestamp=now ,
        action='insert',
        playground=playground,
        log='[{ "field": "name", "from": "", "to": "Strong Reach Playground" }]',
        headers='{"content_length": "18", "host": "111.203.119.43", "content_type": "application/x-www-form-urlencoded"}',
        cookies='',
        revision_group=1
    )

    models.Revision.create(
        timestamp=now,
        action='update',
        playground=playground,
        log='[{ "field": "name", "from": "Strong Reach Playground", "to": "Not So Strong Playground" }, { "field": "safety-fence", "from": 0, "to": 1 }]',
        headers='{"content_length": "18", "host": "26.240.97.59", "content_type": "application/x-www-form-urlencoded"}',
        cookies='',
        revision_group=2
    )

    models.Revision.create(
        timestamp=now,
        action='update',
        playground=playground2,
        log='[{ "field": "facility", "from": "", "to": "Park for Weak Children" }, { "field": "url", "from": "#http://www.bowdon.net/recreation-and-culture/recreation/#", "to": "" }, { "field": "smooth-surface-throughout", "from": 0, "to": 1 }, { "field": "safety-fence", "from": 1, "to": 0 }]',
        headers='{"content_length": "18", "host": "41.202.99.140", "content_type": "application/x-www-form-urlencoded"}',
        cookies='',
        revision_group=2
    )

    models.Revision.create(
        timestamp=now,
        action='update',
        playground=playground,
        log='[{ "field": "safety-fence", "from": 0, "to": 1 }]',
        headers='{"content_length": "18", "host": "117.204.56.109", "content_type": "application/x-www-form-urlencoded"}',
        cookies='',
        revision_group=2
    )

    models.Revision.create(
        timestamp=now,
        action='insert',
        playground=playground2,
        log='[{ "field": "safety-fence", "from": 0, "to": 1 }]',
        headers='{"content_length": "18", "host": "117.204.56.109", "content_type": "application/x-www-form-urlencoded"}',
        cookies='',
        revision_group=2
    )

    models.Revision.create(
        timestamp=now,
        action='delete-request',
        playground=playground,
        log='[{ "field": "safety-fence", "from": 0, "to": 1 }]',
        headers='{"content_length": "18", "host": "117.204.56.109", "content_type": "application/x-www-form-urlencoded"}',
        cookies='',
        revision_group=2
    )


"""
Cron jobs
"""
def cron_test():
    """
    Example cron task. Note we use "local" instead of "run"
    because this will run on the server.
    """
    require('settings', provided_by=[production, staging])

    local('echo $DEPLOYMENT_TARGET > /tmp/cron_test.txt')

"""
Destruction

Changes to destruction require setup/deploy to a test host in order to test.
Destruction should remove all files related to the project from both a remote
host and S3.
"""
def _confirm(message):
    answer = prompt(message, default="Not at all")

    if answer.lower() not in ('y', 'yes', 'buzz off', 'screw you'):
        exit()


def nuke_confs():
    """
    DESTROYS rendered server configurations from the specified server.
    This will reload nginx and stop the uwsgi config.
    """
    require('settings', provided_by=[production, staging])

    for service, remote_path, extension in SERVICES:
        with settings(warn_only=True):
            service_name = '%s.%s' % (app_config.PROJECT_SLUG, service)
            file_name = '%s.%s' % (service_name, extension)
            remote_path = '%s%s' % (remote_path, file_name)

            if service == 'nginx':
                sudo('rm -f %s%s' % (remote_path, file_name))
                sudo('service nginx reload')
            else:
                sudo('service %s stop' % service_name)
                sudo('rm -f %s%s' % (remote_path, file_name))
                sudo('initctl reload-configuration')


def shiva_the_destroyer():
    """
    Deletes the app from s3
    """
    require('settings', provided_by=[production, staging])

    _confirm("You are about to destroy everything deployed to %(settings)s for this project.\nDo you know what you're doing?" % env)

    with settings(warn_only=True):
        s3cmd = 's3cmd del --recursive %s'

        for bucket in env.s3_buckets:
            env.s3_bucket = bucket
            local(s3cmd % ('s3://%(s3_bucket)s/%(project_slug)s' % env))

        if env['deploy_to_servers']:
            run('rm -rf %(path)s' % env)

            if env['deploy_crontab']:
                uninstall_crontab()

            if env['deploy_services']:
                nuke_confs()
