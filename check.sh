set -e  # Exit immediately if a command exits with a non-zero status.

if [ "$1" == "--no-fix" ]; then
    poetry run ruff format --check
    poetry run ruff check --select I
    poetry run ruff check
else
    poetry run ruff format
    poetry run ruff check --fix --select I
    poetry run ruff check --fix
fi

# poetry run mypy slm
# poetry run pyright
poetry check
poetry run pip check
poetry export -f requirements.txt --output requirements.txt --without-hashes
cd ./doc
poetry run doc8 --ignore-path build --max-line-length 100 -q
poetry run make spelling
# check for broken links in the docs ############
set +e

# do not run this in CI - too spurious
if [ "$1" != "--no-fix" ]; then
    poetry run sphinx-build -b linkcheck -q -D linkcheck_timeout=5 ./source ./build > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        cat ./build/output.txt | grep broken
        exit 1
    fi
fi
#################################################
cd ..
