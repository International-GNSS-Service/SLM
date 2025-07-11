from slm import __version__ as slm_version


def globals(request):
    return {"slm_version": slm_version}
