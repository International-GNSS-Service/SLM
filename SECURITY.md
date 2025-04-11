# Security Policy

[![CodeQL](https://github.com/International-GNSS-Service/SLM/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/International-GNSS-Service/SLM/actions/workflows/github-code-scanning/codeql?query=branch:main)
[![Safety](https://github.com/International-GNSS-Service/SLM/workflows/safety/badge.svg)](https://docs.safetycli.com/safety-docs)
[![Zizmor](https://github.com/International-GNSS-Service/SLM/actions/workflows/zizmor.yml/badge.svg?branch=main)](https://woodruffw.github.io/zizmor)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/International-GNSS-Service/SLM/badge)](https://securityscorecards.dev/viewer/?uri=github.com/International-GNSS-Service/SLM)


Only the latest version of the SLM [![PyPI version](https://badge.fury.io/py/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm/) is supported on the versions of Python [![PyPI pyversions](https://img.shields.io/pypi/pyversions/igs-slm.svg)](https://pypi.python.org/pypi/igs-slm/) and Django 
[![PyPI djversions](https://img.shields.io/pypi/djversions/igs-slm.svg)](https://pypi.org/project/igs-slm/) our continuous integrations are currently running on.

## Monitoring Dependencies

The SLM depends on a large stack of upstream software. Not just Django and Python but third party extensions. Before inclusion as a dependency, upstream software is carefully reviewed for stability, ongoing support and trust. We rely on [Safety](https://safetycli.com/) for monitoring upstream vulnerabilities. When a new vulnerability is discovered the security badge on this page will indicate a failure against [our policy](https://github.com/International-GNSS-Service/SLM/blob/master/.safety-policy.yml). We will triage the vulnerability and make one of three decisions:

1. Replace the dependency
2. Upgrade the dependency
3. Exempt the vulnerability in our policy.

If we exempt the vulnerability the reason will be noted in the [policy file](https://github.com/International-GNSS-Service/SLM/blob/master/.safety-policy.yml).


## Reporting a Vulnerability

If you think you have found a vulnerability, and even if you are not sure, please report it to us in private by going to Security -> Advisories -> New Draft Security Advisory or alternatively, email us at cb@igs.org
We will review it and get back to you. Please refrain from public discussions of the issue.
