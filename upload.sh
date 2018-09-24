#!/usr/bin/env bash
python setup.sh sdist
twine upload -r pypi --repository-url https://upload.pypi.org/legacy/ dist/*
