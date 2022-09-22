from slm.settings import set_default
import importlib


set_default('SLM_ROUTINES', {})

SLM_ROUTINES.setdefault('deploy', {}).setdefault('defaults', [
    (0, ['check', [], {'deploy': True}]),
    (10, ['makemigrations', [], {}, lambda: importlib.invalidate_caches()]),
    (11, ['migrate', [], {}]),
    (20, ['renderstatic', []]),
    (21, ['collectstatic', [], {'interactive': False, 'ignore': ['*.scss']}])
])

SLM_ROUTINE_DEPLOY = 'Run collection of commands that likely need to be run whenever code is updated.'
SLM_ROUTINE_DEPLOY_INITIAL = 'Run collection of commands that should only be run on the first deployment.'
