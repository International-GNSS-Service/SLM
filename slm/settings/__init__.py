import inspect

import importlib_resources


def set_default(var_name, default, set_if_none=True):
    """
    Set the value of the given variable in the calling scope to a default value if it has been not been previously
    defined.

    :param var_name: The name of the variable to set in the calling scope.
    :param default: The value to set the variable to if its undefined
    :param set_if_none: Treat the variable as undefined if it is None, default: True
    :return: the variable that was set
    """
    scope = inspect.stack()[1][0].f_globals
    if var_name not in scope or set_if_none and scope[var_name] is None:
        scope[var_name] = default
    return scope[var_name]


def is_defined(var_name):
    """
    Returns true if the given variable has been defined in the calling scope.

    :param var_name: The name of the variable to check for
    :return: True if the variable is defined, false otherwise
    """
    return var_name in inspect.stack()[1][0].f_globals


def resource(package, file):
    profile2 = importlib_resources.files(package) / file
    with importlib_resources.as_file(profile2) as profile2_path:
        return str(profile2_path)

