import os, sys

from fabric.api import *
from fabric.contrib import files, console
from fabric.contrib.project import rsync_project
from fabric import utils
from fabric.decorators import hosts
import posixpath


env.user = 'talks'
env.home = '/home/talks'
env.project = 'talks'
env.code_repo = 'git://github.com/caktus/lightning-talk-lunches.git'


def _setup_path():
    env.root = posixpath.join(env.home, 'www', env.environment)
    env.log_dir = posixpath.join(env.home, 'www', env.environment, 'log')
    env.code_root = posixpath.join(env.root, 'code_root')
    env.project_root = posixpath.join(env.code_root, env.project)
    env.virtualenv_root = posixpath.join(env.root, 'python_env')


def setup_dirs():
    """ create directories """
    run('mkdir -p %(log_dir)s' % env)


def production():
    """ use production environment on remote host"""
    env.code_branch = 'master'
    env.environment = 'production'
    env.hosts = ['talks.caktusgroup.com']
    _setup_path()


def bootstrap():
    """ initialize remote host environment (virtualenv, deploy, update) """
    require('root', provided_by=('staging', 'production'))
    run('mkdir -p %(root)s' % env)
    clone_repo()
    setup_dirs()
    update_services()
    create_virtualenv()
    update_requirements()


def create_virtualenv():
    """ setup virtualenv on remote host """
    require('virtualenv_root', provided_by=('staging', 'production'))
    args = '--clear --distribute --no-site-packages'
    run('virtualenv %s %s' % (args, env.virtualenv_root))


def clone_repo():
    """ clone a new copy of the git repository """
    with cd(env.root):
        run('git clone %(code_repo)s %(code_root)s' % env)


def deploy():
    """ deploy code to remote host by checking out the latest via git """
    require('root', provided_by=('staging', 'production'))
    with cd(env.code_root):
        run('git pull')
        run('git checkout %(code_branch)s' % env)
    update_requirements()


def update_requirements():
    """ update external dependencies on remote host """
    require('code_root', provided_by=('staging', 'production'))
    cmd = ['pip install -q -E %(virtualenv_root)s' % env]
    cmd += ['--requirement %s' % posixpath.join(env.code_root, 'requirements.txt')]
    run(' '.join(cmd))


def update_services():
    """ upload changes to services such as nginx """
    upload_apache_conf()
    apache_reload()
    # netstat_plnt()


def upload_apache_conf():
    dest = posixpath.join(env.home, 'apache.conf.d', 'production.conf')
    put('services/apache-%(environment)s.conf' % env, dest)
    configtest()


def configtest():    
    """ test Apache configuration """
    require('root', provided_by=('staging', 'production'))
    run('apache2ctl configtest')


def apache_reload():    
    """ reload Apache on remote host """
    require('root', provided_by=('staging', 'production'))
    run('sudo /etc/init.d/apache2 reload')


def apache_restart():
    """ restart Apache on remote host """
    require('root', provided_by=('staging', 'production'))
    run('sudo /etc/init.d/apache2 restart')


def netstat_plnt():
    """ run netstat -plnt on a remote host """
    require('hosts', provided_by=('production', 'staging'))
    run('sudo netstat -plnt')
