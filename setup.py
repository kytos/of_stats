"""Setup script.

Run "python3 setup.py --help-commands" to list all available commands and their
descriptions.
"""
import os
import shutil
import sys
from abc import abstractmethod
from pathlib import Path
from subprocess import CalledProcessError, call, check_call

from setuptools import Command, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

if 'bdist_wheel' in sys.argv:
    raise RuntimeError("This setup.py does not support wheels")

# Paths setup with virtualenv detection
if 'VIRTUAL_ENV' in os.environ:
    BASE_ENV = Path(os.environ['VIRTUAL_ENV'])
else:
    BASE_ENV = Path('/')

NAPP_NAME = 'of_stats'
NAPP_VERSION = '1.1.0'
# Kytos var folder
VAR_PATH = BASE_ENV / 'var' / 'lib' / 'kytos'
# Path for enabled NApps
ENABLED_PATH = VAR_PATH / 'napps'
# Path to install NApps
INSTALLED_PATH = VAR_PATH / 'napps' / '.installed'
CURRENT_DIR = Path('.').resolve()

# NApps enabled by default
# CORE_NAPPS = ['of_core']


class SimpleCommand(Command):
    """Make Command implementation simpler."""

    user_options = []

    @abstractmethod
    def run(self):
        """Run when command is invoked.

        Use *call* instead of *check_call* to ignore failures.
        """
    def initialize_options(self):
        """Set default values for options."""

    def finalize_options(self):
        """Post-process options."""


class Cleaner(SimpleCommand):
    """Custom clean command to tidy up the project root."""

    description = 'clean build, dist, pyc and egg from package and docs'

    def run(self):
        """Clean build, dist, pyc and egg from package and docs."""
        call('rm -vrf ./build ./dist ./*.egg-info', shell=True)
        call('find . -name __pycache__ -type d | xargs rm -rf', shell=True)
        call('make -C docs/ clean', shell=True)


# pylint: disable=attribute-defined-outside-init, abstract-method
class TestCommand(Command):
    """Test tags decorators."""

    user_options = [
        ('size=', None, 'Specify the size of tests to be executed.'),
        ('type=', None, 'Specify the type of tests to be executed.'),
    ]

    sizes = ('small', 'medium', 'large', 'all')
    types = ('unit', 'integration', 'e2e')

    def get_args(self):
        """Return args to be used in test command."""
        return '--size %s --type %s' % (self.size, self.type)

    def initialize_options(self):
        """Set default size and type args."""
        self.size = 'all'
        self.type = 'unit'

    def finalize_options(self):
        """Post-process."""
        try:
            assert self.size in self.sizes, ('ERROR: Invalid size:'
                                             f':{self.size}')
            assert self.type in self.types, ('ERROR: Invalid type:'
                                             f':{self.type}')
        except AssertionError as exc:
            print(exc)
            sys.exit(-1)


class Test(TestCommand):
    """Run all tests."""

    description = 'run tests and display results'

    def get_args(self):
        """Return args to be used in test command."""
        markers = self.size
        if markers == "small":
            markers = 'not medium and not large'
        size_args = "" if self.size == "all" else "-m '%s'" % markers
        return '--addopts="tests/%s %s"' % (self.type, size_args)

    def run(self):
        """Run tests."""
        cmd = 'python setup.py pytest %s' % self.get_args()
        try:
            check_call(cmd, shell=True)
        except CalledProcessError as exc:
            print(exc)


class TestCoverage(Test):
    """Display test coverage."""

    description = 'run tests and display code coverage'

    def run(self):
        """Run unittest quietly and display coverage report."""
        cmd = 'coverage3 run setup.py pytest %s' % self.get_args()
        cmd += ' && coverage3 report'
        try:
            check_call(cmd, shell=True)
        except CalledProcessError as exc:
            print(exc)


class Linter(SimpleCommand):
    """Code linters."""

    description = 'lint Python source code'

    def run(self):
        """Run yala."""
        print('Yala is running. It may take several seconds...')
        try:
            check_call('yala *.py', shell=True)
        except CalledProcessError:
            print('Linter check failed. Fix the error(s) above and try again.')
            sys.exit(-1)


class CITest(SimpleCommand):
    """Run all CI tests."""

    description = 'run all CI tests: unit and doc tests, linter'

    def run(self):
        """Run unit tests with coverage, doc tests and linter."""
        cmds = ['python3.6 setup.py ' + cmd
                for cmd in ('coverage', 'lint')]
        cmd = ' && '.join(cmds)
        check_call(cmd, shell=True)


# class KytosInstall:
#     """Common code for all install types."""
#
#     @staticmethod
#     def enable_core_napps():
#         """Enable a NAPP by creating a symlink."""
#         (ENABLED_PATH / 'kytos').mkdir(parents=True, exist_ok=True)
#         for napp in CORE_NAPPS:
#             napp_path = Path('kytos', napp)
#             src = ENABLED_PATH / napp_path
#             dst = INSTALLED_PATH / napp_path
#             src.symlink_to(dst)


class InstallMode(install):
    """Create files in var/lib/kytos."""

    description = 'To install NApps, use kytos-utils. Devs, see "develop".'

    def run(self):
        """Create of_stats as default napps enabled."""
        print(self.description)


class DevelopMode(develop):
    """Recommended setup for kytos-napps developers.

    Instead of copying the files to the expected directories, a symlink is
    created on the system aiming the current source code.
    """

    description = 'Install NApps in development mode'

    def run(self):
        """Install the package in a developer mode."""
        super().run()
        if self.uninstall:
            shutil.rmtree(str(ENABLED_PATH), ignore_errors=True)
        else:
            self._create_folder_symlinks()
            # self._create_file_symlinks()
            # KytosInstall.enable_core_napps()

    @staticmethod
    def _create_folder_symlinks():
        """Symlink to all Kytos NApps folders.

        ./napps/kytos/napp_name will generate a link in
        var/lib/kytos/napps/.installed/kytos/napp_name.
        """
        links = INSTALLED_PATH / 'kytos'
        links.mkdir(parents=True, exist_ok=True)
        code = CURRENT_DIR
        src = links / 'of_stats'
        symlink_if_different(src, code)

        (ENABLED_PATH / 'kytos').mkdir(parents=True, exist_ok=True)
        dst = ENABLED_PATH / Path('kytos', 'of_stats')
        symlink_if_different(dst, src)


def symlink_if_different(path, target):
    """Force symlink creation if it points anywhere else."""
    # print(f"symlinking {path} to target: {target}...", end=" ")
    if not path.exists():
        # print(f"path doesn't exist. linking...")
        path.symlink_to(target)
    elif not path.samefile(target):
        # print(f"path exists, but is different. removing and linking...")
        # Exists but points to a different file, so let's replace it
        path.unlink()
        path.symlink_to(target)


setup(name=NAPP_NAME,
      version=NAPP_VERSION,
      description='Core NApps developed by Kytos Team',
      url='http://github.com/kytos-ng/of_stats',
      author='Kytos Team',
      author_email='of-ng-dev@ncc.unesp.br',
      license='MIT',
      install_requires=['setuptools >= 36.0.1'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      extras_require={
          'dev': [
              'coverage',
              'pip-tools',
              'yala',
              'tox',
          ],
      },
      cmdclass={
          'clean': Cleaner,
          'ci': CITest,
          'coverage': TestCoverage,
          'develop': DevelopMode,
          'install': InstallMode,
          'lint': Linter,
      },
      zip_safe=False,
      classifiers=[
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3.6',
          'Topic :: System :: Networking',
      ])
