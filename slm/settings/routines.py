import importlib

from slm.settings import set_default

set_default('SLM_ROUTINES', {})

SLM_ROUTINES.setdefault('deploy', {}).setdefault('defaults', [
    (0, ['check', [], {'deploy': True}]),
    # force makemigrations to be run manually  - this avoids potential issues
    # when a migration file is not packaged or checked into version control and
    # the server ends up generating its own version of it that will conflict
    # down the line
    # (10, ['makemigrations', [], {}, lambda: importlib.invalidate_caches()]),
    (11, ['migrate', [], {}]),
    (20, ['renderstatic', []]),
    (21, ['collectstatic', [], {'interactive': False, 'ignore': ['*.scss']}])
])

SLM_ROUTINE_DEPLOY = 'Run collection of commands that likely need to be run whenever code is updated.'
SLM_ROUTINE_DEPLOY_INITIAL = 'Run collection of commands that should only be run on the first deployment.'
