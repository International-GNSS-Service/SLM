# Security Policy

[![CodeQL](https://github.com/International-GNSS-Service/SLM/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/International-GNSS-Service/SLM/actions/workflows/github-code-scanning/codeql?query=branch:main)
[![Safety](https://github.com/International-GNSS-Service/SLM/actions/workflows/safety.yml/badge.svg?branch=main)](https://docs.safetycli.com/safety-docs)
[![Zizmor](https://github.com/International-GNSS-Service/SLM/actions/workflows/zizmor.yml/badge.svg?branch=main)](https://docs.zizmor.sh/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/International-GNSS-Service/SLM/badge)](https://securityscorecards.dev/viewer/?uri=github.com/International-GNSS-Service/SLM)


Only the latest version of the SLM is supported on the versions of Python and Django that our continuous integrations are currently running on:

- [![SLM](https://badge.fury.io/py/igs-slm.svg)](https://pypi.org/project/igs-slm/)
- [![Python](https://img.shields.io/pypi/pyversions/igs-slm.svg)](https://pypi.org/project/igs-slm/)
- [![Django](https://img.shields.io/pypi/djversions/igs-slm.svg)](https://pypi.org/project/igs-slm/)

## Monitoring Dependencies

The SLM depends on a large stack of upstream software. Not just Django and Python but third party extensions. Before inclusion as a dependency, upstream software is carefully reviewed for stability, ongoing support and trust. We rely on [Safety](https://safetycli.com/) for monitoring upstream vulnerabilities. When a new vulnerability is discovered the security badge on this page will indicate a failure against [our policy](https://github.com/International-GNSS-Service/SLM/blob/main/.safety-policy.yml). We will triage the vulnerability and make one of three decisions:

1. Replace the dependency
2. Upgrade the dependency
3. Exempt the vulnerability in our policy.

If we exempt the vulnerability the reason will be noted in the [policy file](https://github.com/International-GNSS-Service/SLM/blob/main/.safety-policy.yml).

## Publishing Releases

All releases will have verified tag on github. As of 0.1.5b0 we use [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) to issue all releases.

## Reporting a Vulnerability

If you think you have found a vulnerability, and even if you are not sure, please [report it to us in private](https://github.com/International-GNSS-Service/SLM/security/advisories/new) or alternatively, email us at cb@igs.org. We will review it and get back to you. Please refrain from public discussions of the issue.
