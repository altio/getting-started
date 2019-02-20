# Getting Started
A primer on developing software using Docker, Python, and Django.

1. Setup a linux operating system on a physical or virtual machine. Install
   `git` using your package manager, and then install `docker`, and `docker
   compose` per the websites below:

   - [Install Docker on CentOS](
       https://docs.docker.com/install/linux/docker-ce/centos/
     )
   - [Install Docker on Debian](
       https://docs.docker.com/install/linux/docker-ce/debian/
     )
   - [Install Docker on Fedora](
       https://docs.docker.com/install/linux/docker-ce/fedora/
     )
   - [Install Docker on Ubuntu](
       https://docs.docker.com/install/linux/docker-ce/ubuntu/
     )

   In all cases, make sure you run the post-installation steps to give your
   unprivileged user access:

   - [Docker Post-Installation](
       https://docs.docker.com/install/linux/linux-postinstall/
     )

   Then install docker-compose:

   - [Install Docker Compose](
       https://docs.docker.com/compose/install/
   )

   **_Restart your operating system now._**

1. Checkout this repository, feel free to rename it whatever you want.

   ```
   $ git clone git@github.com:altio/getting_started.git
   $ cd getting_started
   ```

1. Build the django development container image, passing in the current user's
   UID.  This will allow files created in your container to have permissions
   which match your OS user, and avoid having to install any additional
   dependencies on your host OS.

   ```
   $ docker-compose build --build-arg UID=$UID
   ```

   Understand that the goal of this image is *not* to have all of the
   dependencies self-contained as it would be in production.  Instead, we are
   building a containerized "extension" of the host OS that will have the OS
   dependencies (libraries) needed for our python packages to work in this
   project.  This image ought to be a reusable "base" development image that
   can be extended by other django projects to add additional dependencies.
   The python packages themselves will be yielded outside of the container
   so that a) IDEs can attempt introspection, and b) to avoid the re-build
   time every time a python package is added/removed.  This also means that
   part of the bootstrapping process of toggling between branches should be
   to sync the python virtualenv to ensure dependencies did not change.

1. (Optional) Add deployment and/or development dependencies to your python
   environment:

   ```
   $ docker-compose run --rm backend pipenv install <package> --dev --skip-lock
   ```

   * Packages can be separated by spaces.
   * Use the `--dev` flag if the packages are only for dev/build/test use.
   * Use the `--skip-lock` flag if you are going to install more packages
     immediately after this command, otherwise omit it.

1. If you did not already generate a lock file and install your dependencies:

   ```
   $ docker-compose run --rm backend pipenv install --dev
   ```

   Commit the Pipfile.lock file.

1. Now that your container is built and the environment is groomed, you can
   start a django project.  For your convenience, a script is provided that
   adds the docker-compose run --rm for you at "./run," so if you are following
   the [Django tutorial](
     https://docs.djangoproject.com/en/2.1/intro/tutorial01/
   ) you can replace any employments of bash (`$ ...`) with `./run backend ...`,
   e.g.:

   ```
   $ docker-compose run --rm backend django-admin.py startproject <project_name>
   or
   $ ./run backend django-admin.py startproject <project_name>
   ```

   After it is created, you will want to move the contents of the folder up a
   directory to match the expected layout of the Django tutorial and many
   projects, e.g.:

   ```
   $ mv project temp
   $ mv temp/* .
   $ rmdir temp
   ```

   Other options are possible if you wanted to "package" your app, but that is
   outside of the scope of this tutorial.

1. Finally, the django tutorial will reasonably guide you through setting up an
   app and modifying your settings and the general migration workflow.  Rather
   than use SQLite, however, let's use the PostgreSQL database we setup in our
   docker-compose file.  To do this, you will need to modify your project's
   settings file `DATABASES` value as follows:

   ```
   import dj_database_url
   DATABASES = {
       'default': dj_database_url.config()
   }
   ```

   Additionally, a package called `django-extensions` has been provided which
   provides some useful management commands, one of which is a
   database-agnostic, gracefully failing `reset_db` command.  To use it, you
   will need to add it to your `INSTALLED_APPS`, e.g.:

   ```
   INSTALLED_APPS = [
       'django_extensions',
       ...
   ]
   ```

   On occasions where you need to invoke manage.py (`$ python manage.py ...`),
   you can do so with a second helper `./manage ...`, e.g.:
   ```
   $ docker-compose run --rm backend python manage.py startapp <app_name>
   or
   $ ./manage startapp <app_name>
   ```

   Now, you can create your database for the project and migrate it to the
   initial state provided by Django:

   ```
   $ ./manage reset_db
   $ ./manage makemigrations
   $ ./manage migrate
   ```

   Also, if you want to skip ahead a little, you may want to make yourself a
   superuser to login to the admin:

   ```
   $ ./manage createsuperuser
   ```

1. Now that you have bootstrapped the application and related services, you are
   ready to continue tackling the tutorial or building your application.  Since
   we have all of the scaffolding in place, we can bring the site online and
   confirm it is there.  As you make changes, the server will automatically
   reload.  If you make breaking changes, the server may crash, but compose will
   attempt to restart it for you until your code is working again.

   ```
   $ docker-compose up -d
   ```

   Browse to 127.0.0.1:8000.  If you want to access it from another machine,
   that will only require modifying `ALLOWED_HOSTS` in settings and ensuring
   your firewall is permitting access.

1. Keep in mind that as you work on a project with others, they may need to add
   dependencies to the Dockerfile or Pipfile.  To ensure you are consistent each
   time you toggle branches, you can run the following:

   ```
   $ docker-compose kill
   $ docker-compose build
   $ ./run backend pipenv sync --dev
   $ docker-compose up -d
   ```

   **NOTE:** This would be excessive for every checkout.  Just highlighting the
   need to do this when others make changes to the Dockerfile or Pipfile.  If
   there are no changes to either of those, there is no need to rebuild or sync
   the dependencies.

   You should also be attentive to your database state in these cases. Writing
   helpers to backup and restore a known good state of the database and then
   migrate it to the current state of code is prudent.  Again, that is outside
   the scope of this tutorial, but important to consider nonetheless.


# WIP BELOW THIS POINT

## Summary
The goal of this primer to is help new users of Python and Django get started
developing while reinforcing some best practices.  One of the first things
every developer will need is to prepare their environment.  In the past, this
would have been accomplished by downloading and installing countless libraries
and applications before one could even contemplate starting any work.  In the
opinion of this writer, however, you should do no such thing.  Instead, this
document will focus on setting up your environment using some best practices
from the current state of software development.

## Containers and Virtual Environments
Imagine you are a software consultant who is developing two products with
similar (but sufficiently different) requirements.  One is using the current
version of postgres, the other is using two version ago.  One is using Python
2.7 and the other is using Python 3.6.  Furthermore, your operating system has
older versions of some of these applications installed, but upgrading them
might cause some other applications on the operating system to stop working as
expected.  Needless to say, this nightmare scenario is all-too-familiar for
software developers of yesteryear.

Instead, this guide will propose that you get in the habit of _never_
polluting your operating system with project requirements.  Simply put, it is
just a bad idea.  It does not scale, and it introduces difficult-to-reproduce
discrepancies between developers' environments as well as those of your
deployment targets.

To alleviate this, there are two tools one should understand and use: Docker
and Pipenv.

### Containers
Containers can be thought of as minimally-provisioned guest operating systems which
run on your host operating system inside of a self-contained unit.  Users, groups,
networking, and storage can be shared with the host or implemented cleanly inside
the threshold of the container.


Topics to cover:

### Operating Systems

Glossary of Terms

Programming Languages
Assembly and Machine Language
C
Libraries
Operating Systems
Compilation
Python
Packages
Modules
Pip
Virtual Environments
Pipenv
