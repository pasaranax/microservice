#!/usr/bin/env bash

rm -f dist/*
python setup.py sdist
twine upload -r pypi --repository-url https://upload.pypi.org/legacy/ dist/*
