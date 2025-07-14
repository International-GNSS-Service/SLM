"""
These settings utilities help us compose settings across multiple files.

.. warning::

    These functions only work when called from a settings file because
    they operate on the calling scope. Do not call these functions from
    any other location.
"""

import re
import sys
import typing as t
from functools import partial
from os import PathLike
from pathlib import Path

import environ
import importlib_resources
from django.core.exceptions import ImproperlyConfigured

re.Pattern


class _NotGiven:
    pass


_environ: t.Optional[environ.FileAwareEnv] = None
_base_dir: t.Optional[Path] = None
_email_rgx: t.Optional[re.Pattern] = None


def split_email_str(email: str) -> t.Tuple[str, str]:
    """
    Split an email string into display name and email address.

    If there is no display name it will be the empty string.

    :param email: An email string. E.g.:
        * ``name@example.com``
        * ``Last, First <name@example.com>``
        * ``"First Last" <name@example.com>``

    :return: A 2-tuple of (display name, email address)
    """
    global _email_rgx
    if "<" not in email:
        return ("", email)
    if not _email_rgx:
        _email_rgx = re.compile(r"\s+[\"']?(?P<display>.*)[\"']?\s+<(?P<email>.*)>")
    if not (match := _email_rgx.search(email)):
        raise ImproperlyConfigured(f"{email} is not a valid email string.")
    return match.groupdict["display"].strip(), match.groupdict["email"].strip()


def _is_relative_to(parent: Path, child: Path) -> bool:
    # TODO remove when python >=3.9
    if sys.version_info[:2] < (3, 9):
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False
    return child.is_relative_to(parent)


def env(**kwargs) -> environ.FileAwareEnv:
    """
    Fetch the :class:`environ.Env` object that should be used to configure settings.
    If an environment file exists it will be read in. The environment file precendence
    is:

        1. The path in the environment variable SLM_ENV
        2. BASE_DIR / .env

    :return: The :class:`~environ.FileAwareEnv` object configured to read our
        environment variables and files.
    """
    global _environ
    if _environ is None:
        scope = sys._getframe(1).f_globals
        default_env = scope.get("BASE_DIR", "")
        if default_env:
            default_env = str(Path(default_env) / ".env")

        DEBUG = kwargs.pop("DEBUG", (bool, False))
        _environ = environ.FileAwareEnv(DEBUG=DEBUG, **kwargs)
        override_env = _environ.str("SLM_ENV", scope.get("SLM_ENV", default_env))
        if override_env and Path(override_env).is_file():
            _environ.read_env(str(override_env))
    return _environ


def base_dir(scope=None) -> Path:
    """
    Fetch the :setting:`BASE_DIR`, this will raise an
    :exc:`~django.core.exceptions.ImproperlyConfigured` exception if it does not exist yet.

    :param scope: The settings scope (do not pass if calling from a settings file)
    :return: The :setting:`BASE_DIR` as a :class:`pathlib.Path` object.
    :raises: :exc:`~django.core.exceptions.ImproperlyConfigured` if :setting:`BASE_DIR` is not
        defined.
    """
    global _base_dir
    if not _base_dir:
        scope = scope or sys._getframe(1).f_globals
        _base_dir = scope.get("BASE_DIR", None)
        if _base_dir is None:
            raise ImproperlyConfigured("BASE_DIR was needed before it was defined!")
        _base_dir = Path(_base_dir)
        if not _base_dir.is_dir():
            if scope.get("DEBUG", False):
                _base_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
            else:
                raise ImproperlyConfigured(
                    f"BASE_DIR: {_base_dir} is not a directory that exists."
                )
    return _base_dir


def set_default(var_name: str, default: t.Any, set_if_none: bool = True) -> t.Any:
    """
    Set the value of the given variable in the calling scope to a default value if it has been not been previously
    defined.

    :param var_name: The name of the variable to set in the calling scope.
    :param default: The value to set the variable to if its undefined
    :param set_if_none: Treat the variable as undefined if it is None, default: True
    :return: the variable that was set
    """
    scope = sys._getframe(1).f_globals
    if var_name not in scope or set_if_none and scope[var_name] is None:
        scope[var_name] = default
    return scope[var_name]


def is_defined(var_name: str) -> bool:
    """
    Returns true if the given variable has been defined in the calling scope.

    :param var_name: The name of the variable to check for
    :return: True if the variable is defined, false otherwise
    """
    return var_name in sys._getframe(1).f_globals


def get_setting(var_name: str, default: t.Any = _NotGiven) -> t.Any:
    """
    Returns the value of the setting if it exists, if it does not exist the value
    given to default is returned. If no default value is given and the setting
    does not exist a NameError is raised

    :param var_name: The name of the variable to check for
    :param default: The default value to return if the variable does not exist
    :raises NameError: if the name is undefined and no default is given.
    """
    value = sys._getframe(1).f_globals.get(var_name, default)
    if value is _NotGiven:
        raise NameError(f"{var_name} setting variable is not defined.", name=var_name)
    return value


def slm_path(
    value: str, must_exist: bool = False, mk_dirs: bool = False
) -> t.Optional[str]:
    """
    Resolve a configuration path. If the path is relative it will be resolved under
    :setting:`BASE_DIR`. If the value is falsey it will be returned as-is even if
    ``must_exist`` is set.

    :param value: The path as a string
    :param must_exist: If True, raise an
        :exc:`~django.core.exceptions.ImproperlyConfigured` if the path does not exist.
    :param mk_dirs: If True and the path is relative to :setting:`BASE_DIR` create the
        path as a directory if it does not already exist.
    :raises: :exc:`~django.core.exceptions.ImproperlyConfigured` if :setting:`BASE_DIR` is
        needed but not defined, or does not exist or if ``must_exist`` is ``True`` but the
        path does not exist.
    """
    if not value:
        return value
    pth = Path(str(value))

    if relative := not pth.is_absolute():
        pth = base_dir(sys._getframe(1).f_globals) / pth

    if not pth.exists() and mk_dirs:
        relative = relative or _is_relative_to(
            base_dir(sys._getframe(1).f_globals), pth
        )
        if relative:
            pth.mkdir(
                mode=0o775 if sys._getframe(1).f_globals.get("DEBUG", False) else 0o770,
                parents=True,
                exist_ok=True,
            )

    if must_exist and not pth.exists():
        raise ImproperlyConfigured(f"{pth} does not exist!")
    return str(pth)


slm_path_must_exist = partial(slm_path, must_exist=True)
"""
A shortcut for :func:`~slm.settings.slm_path` with ``must_exist=True``.
"""

slm_path_mk_dirs_must_exist = partial(slm_path, must_exist=True, mk_dirs=True)
"""
A shortcut for :func:`~slm.settings.slm_path` with ``must_exist=True`` and
``mk_dirs=True``.
"""


def unset(var_name: str):
    """
    Unset the value of the given variable in the calling scope.

    :param var_name: The name of the variable to unset in the calling scope.
    """
    scope = sys._getframe(1).f_globals
    if var_name in scope:
        del scope[var_name]


def resource(package: str, file: PathLike):
    """
    Use a packaged resource file as a settings file include. If you are
    including a settings file from another package you should pass this to
    split_settings.tools.include:

        .. code-block:: python

            include(resource("slm.settings", "root.py"))

    :param package: The string import path of the package containing the module
    :param file: The name of the python settings module
    :return: The full string path to the resource.
    """
    profile2 = importlib_resources.files(package) / file
    with importlib_resources.as_file(profile2) as profile2_path:
        return str(profile2_path)
