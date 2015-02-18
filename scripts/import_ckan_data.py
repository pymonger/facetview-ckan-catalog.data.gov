#!/usr/bin/env python
import os, sys, json, requests, types, re
import requests_cache
from pyes import ES

from ckan import create_app


requests_cache.install_cache('ckan-import')


TEMPORAL_EXT_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2})(\d{2})(\d{2})$')
TEMPORAL_EXT_FIELDS = ['temporal-extent-begin', 'temporal-extent-end']


def get_es_conn(es_url, index):
    """Create connection and create index if it doesn't exist."""

    conn = ES(es_url)
    if not conn.indices.exists_index(index):
        conn.indices.create_index(index)
    return conn


def ckan_post(url, data):
    """Helper to make post requests to CKAN and work around header bug:
       http://trac.ckan.org/ticket/2942.html"""

    return requests.post(url, data=json.dumps(data), headers={
                           'content-type': 'application/x-www-form-urlencoded'
                         })


def index_group_datasets(ckan_url, es_url, index, group):
    """Index CKAN datasets into ElasticSearch."""

    conn = get_es_conn(es_url, index)

    # package search url template
    ps_url = "%s/action/package_search" % ckan_url

    # get total number of datasets
    r = requests.get(ps_url)
    r.raise_for_status()
    results = r.json()
    total = results['result']['count']

    rows = 100
    start = 1
    datasets = {}
    errors = {}
    while True:
        r = requests.get(ps_url, params={'rows':rows, 'start':start})
        r.raise_for_status()
        results = r.json()
        for res in results['result']['results']:
            if res['type'] != 'dataset': continue
            # check for group
            for g in res['groups']:
                if g['name'] == group:
                  # fix extras
                  extras_fixed = {}
                  for e in res['extras']:
                      key = e['key']
                      value = e['value']
                      if key == "_id": continue

                      # handle extra tags and append to root tags
                      if key == 'tags':
                          if ' > ' in value:
                              value = [i.strip() for i in value.split('>')]
                          elif value.startswith('{'):
                              value = value[1:-2].split(',')
                          else:
                              value = value.split(',')
                          res['tags'].extend([{'name': v} for v in value])

                      # fix temporal extents
                      if key in TEMPORAL_EXT_FIELDS:
                          match = TEMPORAL_EXT_RE.search(value)
                          if match:
                              value = "%s:%s:%s" % match.groups()
                          else: continue

                      # add
                      extras_fixed[key] = value
                  res['extras'] = extras_fixed

                  # add GeoJSON if defined (for now only bbox)
                  lat_min = res['extras'].get('bbox-south-lat', None)
                  lat_max = res['extras'].get('bbox-north-lat', None)
                  lon_min = res['extras'].get('bbox-west-long', None)
                  lon_max = res['extras'].get('bbox-east-long', None)
                  if lat_min is not None and lat_max is not None and \
                     lon_min is not None and lon_max is not None:
                      lat_min = float(lat_min)
                      lat_max = float(lat_max)
                      lon_min = float(lon_min)
                      lon_max = float(lon_max)
                      if lon_min == 0. and lon_max == 360.:
                          lon_min = -180.
                          lon_max = 180.
                      if lon_min == -180.: lon_min = -179.9
                      elif lon_min > 180.: lon_min -= 360.
                      if lon_max == 180.: lon_max = 179.9
                      elif lon_max > 180.: lon_max -= 360.
                      if lat_min == -90.: lat_min = -89.9
                      if lat_max == 90.: lat_max = 89.9
                      res['facetview_location'] = {
                          "type": "polygon",
                          "coordinates": [[
                              [ lon_min, lat_min ],
                              [ lon_min, lat_max ],
                              [ lon_max, lat_max ],
                              [ lon_max, lat_min ],
                              [ lon_min, lat_min ]
                          ]]
                      }
          
                  # index
                  try: conn.index(res, index, 'data.gov', res['id'])
                  except Exception, e:
                      print("Got error: %s" % str(e))
                      errors[res['id']] = res
                      with open('errors/%s.json' % res['id'], 'w') as f:
                          json.dump(res, f, indent=2)
                      continue
                  datasets[res['id']] = True
                  #print(json.dumps(res, indent=2))
        total -= rows
        start += rows
        print("Left to index: %d" % total)
        if total <= 0: break 

    #print("\n".join(datasets))


if __name__ == "__main__":
    env = os.environ.get('CKAN_ENV', 'prod')
    app = create_app('ckan.settings.%sConfig' % env.capitalize(), env=env)
    es_url = app.config['ELASTICSEARCH_URL']
    ckan_url =  app.config['CKAN_REST_URL']
    index = app.config['MERGED_ELASTICSEARCH_INDEX']

    index_group_datasets(ckan_url, es_url, index, 'climate5434')
