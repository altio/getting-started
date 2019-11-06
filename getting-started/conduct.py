#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
from __future__ import print_function
import sys
if sys.version_info[0] == 3 and sys.version_info[1] > 5:
    from collections.abc import Mapping
    import argcomplete
    import argparse
    import dotenv
    from functools import partial
    import hashlib
    import os
    import shlex
    import subprocess
    import sys
    import yaml
else:
    print('This script only works on Python 3.6 and after.  The future is now!')
    exit(1)

# load dotenv into ENV
dotenv.load_dotenv()

# colors
RED = "\033[1;31;1m"
GREEN = "\033[0;32;1m"
YELLOW = "\033[0;33;1m"
END = "\033[0;0m"

# py 3.6+ dicts are ordered... this prevents alpha sorting
yaml.add_representer(dict, lambda dumper, data: dumper.represent_dict(data.items()))

SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))
ENSEMBLE_NAMESPACE = os.getenv('ENSEMBLE_NAMESPACE', os.path.basename(SCRIPTDIR))


def retcode(cmdline):
    sys.stdout.write(GREEN + 'RUN {}'.format(cmdline) + END + '\n')
    return subprocess.call(shlex.split(cmdline))


def output(cmdline):
    sys.stdout.write(GREEN + 'RUN {}'.format(cmdline) + END + '\n')
    return subprocess.check_output(shlex.split(cmdline))


def run(cmdline):
    sys.stdout.write(GREEN + 'RUN {}'.format(cmdline) + END + '\n')
    # proc = subprocess.Popen(shlex.split(cmdline))
    proc = subprocess.Popen(cmdline, shell=True)
    proc.communicate()
    return proc.returncode


# TODO: consider adding base
DEVELOP = 'develop'
COMMANDS = 'commands'
DEPLOY = 'deploy'
DEPENDENCIES = 'dependencies'
EXTENSIONS = ('yaml', 'yml')

# TODO: unset this...
REPO = 'altio'

# TODO: move to yaml
target_files = {
    'base': ['Dockerfile'],
    'dev': ['Dockerfile', 'Pipfile.lock'],
}


def sha1(path, basenames):
    hash = hashlib.sha1()
    assert isinstance(basenames, list)
    for basename in basenames:
        filename = os.path.join(path, basename)
        with open(filename) as fd:
            hash.update(fd.read().encode())
    return hash.hexdigest()[:12]


def get_docker_image_tag(target, path):
    # TODO: will need to write this out to each of the intermediate files for it to work as expected
    #       due to DOCKER_IMAGE_TAG being squashed
    # TODO: for this to work in depth in the mean time, can hash all target files for all layers
    #       and determine need to/act on building if any in tree break
    # TODO: have git rev-parse respect path?  for now will use "project" hash
    # TODO: roll-up python/npm version into the deploy tag
    #       (preferentially lean on python version from setuptools that respects vcs)

    return (
        sha1(path, target_files.get(target))
        if target != DEPLOY
        else output('git rev-parse HEAD').decode()[:12]
    )


def get_tagged_image_name(repo, service, target, tag=None):
    repo = repo + '/' if repo else ''
    if not tag:
        tag = get_docker_image_tag(target)
    return f'{repo}{service}-{target}:{tag}'


def docker_build(tagged_image_name, dockerfile='.', target=None):
    return retcode('docker build {dockerfile} {target}-t {tagged_image_name}'.format(
        dockerfile=dockerfile,
        target=f'--target {target} ' if target else '',
        tagged_image_name=tagged_image_name,
    ))


def recursive_update(tgt, src):
    for key, val in src.items():
        # intentionally break on a type mismatch
        tgt[key] = recursive_update(tgt.get(key, {}), val) if isinstance(val, Mapping) else val
    return tgt


class Conductor(argparse.ArgumentParser):

    def __init__(self, *args, **kwargs):
        kwargs['prog'] = 'conduct.py'
        super(Conductor, self).__init__(*args, **kwargs)
        self.add_argument(
            '--deploy', dest='deploy', action='store_true',
            help='Execute the command in the deployment context.'
        )
        # TODO: review this and confirm there is still value
        self.add_argument(
            '--namespace', dest='namespace', action='store', default=ENSEMBLE_NAMESPACE,
            help='Execute the command in the deployment context.'
        )
        # cache the deploy flag and positional args on each (sub-)parser
        args = self.parse_known_args()
        self.deploy = args[0].deploy
        self.positionals = args[1]
        self.ensemble = self.pull_and_validate()

    @property
    def activity_basenames(self):
        # TODO: this could be cached but not worth the time/added complexity to impl. right now
        # TODO: consider flattening deps and cmds into a single yaml file
        dct = {
            DEPENDENCIES: DEPENDENCIES,
            COMMANDS: COMMANDS,
            DEPLOY: 'docker-compose',
        }
        if not self.deploy:
            dct[DEVELOP] = 'docker-compose.dev'
        return dct

    def pull_and_validate(self, execpath=os.path.curdir, relpath=os.path.curdir):
        """
        Pull and validate dependencies and this project.
        :param execpath: relative path for this run of the method
        :return: dict, complete for this run of the method
        """
        # TODO: set up peers in addition to dependencies... define rules for engagement
        #       peers ought to be able to exist at every level, can be diffed to confirm
        #       they are the same at each level, and then should be independently
        #       controlled rather than as part of the stack
        #       e.g. core services are better modelled as peers for other than simple apps
        execpath = os.path.normpath(os.path.join(execpath, relpath))
        current = {
            'execpath': execpath,
            'relpath': relpath,
            'compose_files': [],
        }
        for activity, basename in self.activity_basenames.items():
            for ext in EXTENSIONS:
                filename = '.'.join((basename, ext))
                relfilename = os.path.join(execpath, filename)
                try:
                    with open(relfilename) as fo:
                        dct = yaml.load(fo.read())
                    if activity in (DEPENDENCIES, COMMANDS):
                        current[activity] = dct[activity]
                    else:
                        current[activity] = dct
                        current['compose_files'].append(filename)
                    break  # no need to try other extensions
                except FileNotFoundError:
                    # if we are on second pass of looking for dependencies file
                    if basename == self.activity_basenames[DEPENDENCIES] and ext == EXTENSIONS[-1] and execpath == os.path.curdir:
                        raise FileNotFoundError(f'There must be a top-level dependencies file.')
                    # if we are on second pass of looking for docker-compose.yml in a dependency path
                    if basename == self.activity_basenames[DEPLOY] and ext == EXTENSIONS[-1] and execpath != os.path.curdir:
                        raise FileNotFoundError(f'There must be a docker-compose file for all dependencies.')
                    continue

        for name in current.get(DEPENDENCIES, {}):
            dct = self.pull_and_validate(execpath, os.path.join(DEPENDENCIES, name))
            if dct:
                current[DEPENDENCIES][name] = (
                    recursive_update(current[DEPENDENCIES][name], dct)
                    if current[DEPENDENCIES][name]
                    else dct
                )

        return current

    def add_builtin_commands(self, subparsers, positionals):
        compose = subparsers.add_parser('compose')
        compose.add_argument(dest='remainder', nargs=argparse.REMAINDER)
        compose.set_defaults(method=self.do_compose, positionals=positionals)
        build = subparsers.add_parser('build')
        build.add_argument(
            '--push', dest='push', action='store_true',
            help='Push the image to the repo.'
        )
        build.add_argument(dest='remainder', nargs=argparse.REMAINDER)
        build.set_defaults(method=self.do_build, positionals=positionals)

    def add_dependency_subparsers(self, dct=None, positionals=[]):
        # do the current level (at a minimum, top-level)
        subparsers = self.add_subparsers()
        if not dct:
            dct = self.ensemble
        self.add_builtin_commands(subparsers=subparsers, positionals=positionals)
        for command_name, command_config in dct.get(COMMANDS, {}).items():
            command_name = command_name.replace('-', '_')
            try:
                extended_command_name = command_config['extends']
            except KeyError:
                raise KeyError(
                    f'Command "{command_name}" in context {positionals} must '
                    f'extend an existing command (e.g. extends: compose).'
                )
            extended_command_name = extended_command_name.replace('-', '_')
            try:
                extended_method = getattr(self, f'do_{extended_command_name}')
            except AttributeError:
                raise AttributeError(
                    f'Extended command "{extended_command_name}" in context '
                    f'{positionals} has could not extend "{command_name}" '
                    f'because no command by that name exists.'
                )
            try:
                extended_args = command_config['args']
            except KeyError:
                raise KeyError(
                    f'Extended command "{extended_command_name}" in context '
                    f'{positionals} has no args.'
                )
            command_method = getattr(self, f'do_{command_name}', None)
            if command_method:
                raise KeyError(
                    f'Command "{command_name}" in context {positionals} '
                    f'already exists. Duplicates are not allowed.'
                )

            setattr(self, f'do_{command_name}', partial(extended_method, *[extended_args]))
            command_method = getattr(self, f'do_{command_name}')

            command_parser = subparsers.add_parser(command_name)
            command_parser.add_argument(dest='remainder', nargs=argparse.REMAINDER)
            command_parser.set_defaults(method=command_method, positionals=positionals)

        # now deal with any children
        for dep_name, dep_dct in dct.get(DEPENDENCIES, {}).items():
            dep_parser = subparsers.add_parser(dep_name)
            dep_parser.add_dependency_subparsers(dep_dct, positionals + [dep_name])

    def get_compose_files(self, dct, execpath=os.path.curdir):
        # compose files override left-to-right
        # so we want the child-most, top-most (bottom of stack) files first, thus we deal with children first
        # next, we yield the deploy file followed by optional dev file
        for child in dct.get('dependencies', {}).values():
            for f in self.get_compose_files(child, execpath=os.path.normpath(os.path.join(execpath, child['relpath']))):
                yield f
        for f in dct['compose_files']:
            yield os.path.normpath(os.path.join(execpath, f))

    def get_execution_context(self, parsed_args):
        dct = self.ensemble
        for positional in parsed_args.positionals:
            dct = dct[DEPENDENCIES][positional]
        return dct

    def do_compose(self, *intermediate_args, parsed_args):
        execution_context = self.get_execution_context(parsed_args)
        project_directory = execution_context['execpath']
        compose_files = ' '.join((
            '-f {}'.format(f)
            for f in self.get_compose_files(execution_context, execution_context['execpath'])
        ))
        context = f'--project-name {ENSEMBLE_NAMESPACE} --project-directory {project_directory} {compose_files}'

        target = 'deploy' if self.deploy else 'dev'
        docker_image_tag = get_docker_image_tag(target, project_directory)

        args = ' '.join(intermediate_args)
        args = ' '.join([args, ' '.join(parsed_args.remainder)])
        cmdline = f'DOCKER_IMAGE_TAG={docker_image_tag} docker-compose {context} {args}'
        return run(cmdline)

    def docker_pull_or_build_and_push_base(self, parsed_args):
        dct = self.ensemble
        for pos in parsed_args.positionals:
            dct = dct['dependencies'][pos]
        dockerfile = '/'.join((dct['execpath'], 'Dockerfile'))
        target = 'base'
        tagged_image_name = get_tagged_image_name(REPO, parsed_args.positionals[-1], target, get_docker_image_tag(target))
        build_required = retcode(f'docker pull {tagged_image_name}')
        build_failed = retcode(f'docker build {dockerfile} --target {target} -t {tagged_image_name}') if build_required else False
        push_attempted = parsed_args.push and build_required and not build_failed
        push_failed = retcode(f'docker push {tagged_image_name}') if push_attempted else False
        return build_required, build_failed, push_attempted, push_failed

    def compose_pull_or_build_and_push(self, parsed_args):
        ret = self.do_compose('build --pull', parsed_args=parsed_args)
        if parsed_args.push:
            ret = ret or self.do_compose('push', parsed_args=parsed_args)
        return ret

    def do_build(self, parsed_args):
        # TODO: come back to this... probably want to do this via compose as well
        # self.docker_pull_or_build_and_push_base(parsed_args)
        return self.compose_pull_or_build_and_push(parsed_args)

    def execute(self):
        argcomplete.autocomplete(self)
        parsed_args = self.parse_args()
        if hasattr(parsed_args, 'method'):
            return parsed_args.method(parsed_args=parsed_args)
        return self.print_usage()


if __name__ == '__main__':
    conductor = Conductor()
    conductor.add_dependency_subparsers()
    sys.exit(conductor.execute())
