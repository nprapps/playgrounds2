#!/usr/bin/env python

import datetime
import json
import os
import time

import boto.cloudsearch
import boto.ses
from fabric.api import *
from fabric.operations import get
from jinja2 import Template
import pytz
import requests

import app
import app_config
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
    env.cloud_search_proxy_base_url = 'http://%s/%s' % (env.hosts[0], app_config.PROJECT_SLUG)
    env.s3_base_url = 'http://%s/%s' % (env.s3_buckets[0], app_config.PROJECT_SLUG)
    env.server_base_url = 'http://%s/%s' % (env.hosts[0], app_config.PROJECT_SLUG)

def staging():
    env.settings = 'staging'
    env.s3_buckets = app_config.STAGING_S3_BUCKETS
    env.hosts = app_config.STAGING_SERVERS
    env.cloud_search_proxy_base_url = 'http://%s/%s' % (env.hosts, app_config.PROJECT_SLUG)
    env.s3_base_url = 'http://%s/%s' % (env.s3_buckets, app_config.PROJECT_SLUG)
    env.server_base_url = 'http://%s/%s' % (env.hosts, app_config.PROJECT_SLUG)

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
    data.less()

def jst():
    """
    Render Underscore templates to a JST package.
    """
    data.jst()

def update_copy():
    """
    Fetches the latest Google Doc and updates local JSON.
    """
    os.system('curl -o data/copy.xls "%s"' % app_config.COPY_URL)

def app_config_js():
    """
    Render app_config.js to file.
    """
    data.app_config_js()

def render_playgrounds():
    data.render_playgrounds()

def remote(fab_command):
    """
    Fab remote:foo runs the fab command foo remotely on the server.
    We call it "fabcasting."
    """
    require('settings', provided_by=[production, staging])
    run('cd %s && bash cron.sh fab %s $DEPLOYMENT_TARGET %s' % (env.repo_path, env.branch, fab_command))

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

    compiled_includes = [] 

    for rule in app.app.url_map.iter_rules():
        rule_string = rule.rule
        name = rule.endpoint

        if name == 'static' or name.startswith('_'):
            print 'Skipping %s' % name
            continue

        if rule_string.endswith('/'):
            filename = 'www' + rule_string + 'index.html'
        elif rule_string.endswith('.html') or rule_string.endswith('.xml') or rule_string.endswith('.js'):
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

    # We choose a sample playground to render so its JS will
    # be rendered. We don't deploy it.
    sample_playgrounds = models.Playground.select().limit(1)
    data.render_playgrounds(sample_playgrounds, compiled_includes)

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

def tests():
    """
    Run Python unit tests.
    """
    with settings(warn_only=True):
        local('mv playgrounds.db playgrounds.db.bak')
        local('mv data/changes.json data/changes.json.bak')

        local('nosetests --with-coverage --cover-html --cover-html-dir=.coverage-html --cover-package=app,data,models,public_app')

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
    run('cd %(repo_path)s; npm install less universal-jst' % env)

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
    data.deploy_to_s3(src)

def _gzip(src='www', dst='gzip'):
    """
    Gzips everything in www and puts it all in gzip
    """
    data.gzip(src, dst)
    os.system('rm -rf %s/live-data' % dst)

    if os.environ.get('DEPLOYMENT_TARGET', None) not in ['production', 'staging']:
        os.system('rm -rf %s/sitemap.xml' % dst)


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


def write_data_json():
    data.write_data_json()


def write_data_csv():
    data.write_data_csv()


def deploy_data():
    """
    Deploy the latest data to S3.
    """
    write_data_csv()
    write_data_json()

    require('settings', provided_by=[production, staging])

    if (env.settings == 'production' and env.branch != 'stable'):
        _confirm("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env)

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    for filename in ['npr-accessible-playgrounds.csv', 'npr-accessible-playgrounds.json']:
        s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --guess-mime-type --recursive sync %s %s'

        for bucket in app_config.S3_BUCKETS:
            os.system(s3cmd % ('www/%s' % filename, 's3://%s/%s/' % (bucket, app_config.PROJECT_SLUG)))

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)


def deploy(remote='origin'):
    """
    Deploy the latest app to S3 and, if configured, to our servers.
    """
    require('settings', provided_by=[production, staging])

    if env.get('deploy_to_servers', False):
        require('branch', provided_by=[stable, master, branch])

    if (env.settings == 'production' and env.branch != 'stable'):
        _confirm("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env)

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    render()
    _gzip()
    _deploy_to_s3()

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

    if env['deploy_to_servers']:
        checkout_latest(remote)

        if env['deploy_crontab']:
            install_crontab()

        if env['deploy_services']:
            deploy_confs()


def write_snapshots():
    require('settings', provided_by=[production, staging])

    if (env.settings == 'production' and env.branch != 'stable'):
        _confirm("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env)

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    os.system('rm -rf .backups_gzip')
    os.system('rm -rf data/backups/.placeholder')

    data.gzip('data/backups', '.backups_gzip')

    s3cmd = 's3cmd -P --add-header=Cache-Control:max-age=5 --guess-mime-type --recursive --exclude-from gzip_types.txt sync %s/ %s'
    s3cmd_gzip = 's3cmd -P --add-header=Cache-Control:max-age=5 --add-header=Content-encoding:gzip --guess-mime-type --recursive --exclude "*" --include-from gzip_types.txt sync %s/ %s'

    for bucket in app_config.S3_BUCKETS:
        os.system(s3cmd % ('.backups_gzip', 's3://%s/%s/backups/' % (bucket, app_config.PROJECT_SLUG)))
        os.system(s3cmd_gzip % ('.backups_gzip', 's3://%s/%s/backups/' % (bucket, app_config.PROJECT_SLUG)))

    os.system('rm -rf .backups_gzip')
    os.system('rm -rf data/backups')
    os.system('mkdir -p data/backups')
    os.system('touch data/backups/.placeholder')

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)


def deploy_playgrounds():
    require('settings', provided_by=[production, staging])

    if (env.settings == 'production' and env.branch != 'stable'):
        _confirm("You are trying to deploy the '%(branch)s' branch to production.\nYou should really only deploy a stable branch.\nDo you know what you're doing?" % env)

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    os.system('rm -rf .playgrounds_html')
    os.system('rm -rf .playgrounds_gzip')

    render_playgrounds()
    _gzip('.playgrounds_html', '.playgrounds_gzip')
    _deploy_to_s3('.playgrounds_gzip')

    _gzip()
    _deploy_to_s3()

    os.system('rm -rf .playgrounds_html')
    os.system('rm -rf .playgrounds_gzip')

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

"""
Application specific
"""
def _download_data():
    """
    Download the latest playgrounds data CSV.
    """
    print 'Cloning database from %s...' % env.settings

    get(remote_path='%(repo_path)s/playgrounds.db' % env, local_path='playgrounds.db')
    #local('curl -o data/playgrounds.csv "%s"' % app_config.DATA_URL)

def load_data():
    """
    Clear and reload playground data from CSV into sqlite.
    """
    """
    models.delete_tables()
    models.create_tables()
    data.load_playgrounds()
    """
    print 'Deprecated! Databases should now be cloned from staging/production for local testing. Use "local_bootstrap".'

def runserver(port='8000'):
    """
    Use local runserver.
    """
    local('gunicorn -b 0.0.0.0:%s app:app' % port)

def local_bootstrap():
    """
    Get and load all data required to make the app run.
    """
    require('settings', provided_by=[production, staging], used_for='specifying which server to clone the database from. (Usually "staging".)')

    update_copy()
    _download_data()

def bootstrap():
    """
    require('settings', provided_by=[production, staging])
    local_bootstrap()
    put(local_path='playgrounds.db', remote_path='%(repo_path)s/playgrounds.db' % env)
    """
    print 'Deprecated! Remote database is now the canonical version. Did you mean "local_bootstrap"?'

def process_updates():
    if os.environ.get('DEPLOYMENT_TARGET', None) in ['production', 'staging']:
        try:
            write_snapshots()
            prepare_changes()
            deploy_playgrounds()
            update_search_index()
            deploy_data()
        except:
            import traceback

            connection = boto.ses.connect_to_region('us-east-1')
            connection.send_email(
                'NPR News Apps <nprapps@npr.org>',
                'Playgrounds Cron Error! (%s, %s)' % (os.environ.get('DEPLOYMENT_TARGET'), datetime.datetime.now(pytz.utc).replace(tzinfo=pytz.utc).strftime('%m/%d')),
                traceback.format_exc() + '\n\nPlease see the README docs for details on how to resolve this: https://github.com/nprapps/playgrounds2#if-cron-fails',
                'nprapps@npr.org')

    else:
        prepare_changes()

def prepare_changes():
    path = './'

    if os.environ.get('DEPLOYMENT_TARGET', None) in ['production', 'staging']:
        path = '%s' % env.repo_path

    now_datetime = datetime.datetime.now(pytz.utc)
    now = time.mktime(now_datetime.timetuple())

    changes = 0

    if os.path.exists('%s/data/changes.json' % path):

        os.system('rm -rf %s/.playgrounds_html/' % path)
        os.system('rm -rf %s/.playgrounds_gzip/' % path)
        os.system('cp %s/playgrounds.db data/backups/%s-playgrounds.db' % (path, now))
        os.system('cp %s/data/changes.json data/backups/%s-changes.json' % (path, now))
        os.system('mv %s/data/changes.json %s/changes-in-progress.json' % (path, path))

        # Create our list of changed items and a revision group.
        changed_playgrounds, revision_group = data.process_changes()

        # Render updated sitemap.
        data.render_sitemap()

        # Render updated index.
        render()

        # Send the revision email.
        data.send_revision_email(revision_group)

        # Remove files and old state.
        os.system('rm -f %s/changes-in-progress.json' % path)
        os.system('rm -rf %s/.playgrounds_html/' % path)
        os.system('rm -rf %s/.playgrounds_gzip/' % path)

        # Show changes.
        changes = len(changed_playgrounds)

    else:
        context = {}
        context['total_revisions'] = 0
        context['deletes'] = {}
        context['deletes']['playgrounds'] = []
        context['deletes']['total_revisions'] = 0
        context['inserts'] = {}
        context['inserts']['playgrounds'] = []
        context['inserts']['total_revisions'] = 0
        context['updates'] = {}
        context['updates']['playgrounds'] = []
        context['updates']['total_revisions'] = 0

        with open('%s/templates/_email.html' % path, 'rb') as read_template:
            payload = Template(read_template.read())

        payload = payload.render(**context)
        addresses = app_config.ADMIN_EMAILS
        data.send_email(addresses, payload)

    print '%s changes | %s' % (changes, now_datetime.isoformat())


def update_search_index(playgrounds=None):
    """
    Batch upload playgrounds to CloudSearch as SDF.
    """
    require('settings', provided_by=[production, staging])

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    data.update_search_index(playgrounds)

    # Un-fake-out deployment target
    app_config.configure_targets(deployment_target)

def clear_search_index():
    """
    Clear all documents from the search index. We use a hack for this:
    Iterate through a wide range of unique id's and issue a delete for
    all of them. This way we pick up one's that might not be in our
    local database anymore.
    """
    require('settings', provided_by=[production, staging])

    _confirm("You are about to delete the %(settings)s search index for this project.\nDo you know what you're doing?" % env)

    # Fake out deployment target
    deployment_target = app_config.DEPLOYMENT_TARGET
    app_config.configure_targets(env.get('settings', None))

    print 'Generating SDF batch...'
    sdf = []

    for i in range(0, 10000):
        sdf.append({
            'type': 'delete',
            'id': '%s_%i' % (app_config.DEPLOYMENT_TARGET, i),
            'version': int(time.time())
        })

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

def load_from_google_spreadsheet(key):
    data.load_from_google_spreadsheet(key)


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

        clear_search_index()

        if env['deploy_to_servers']:
            run('rm -rf %(path)s' % env)

            if env['deploy_crontab']:
                uninstall_crontab()

            if env['deploy_services']:
                nuke_confs()
