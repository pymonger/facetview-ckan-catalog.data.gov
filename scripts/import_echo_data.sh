#!/bin/bash

source $HOME/env/bin/activate
cd $HOME/ops/facetview-ckan-catalog.data.gov/scripts
./import_echo_data.py
