#!/usr/bin/env python
import os, sys, json, requests, types, re
import requests_cache
from pyes import ES

from ckan import create_app


requests_cache.install_cache('echo-import')



def get_es_conn(es_url, index):
    """Create connection and create index if it doesn't exist."""

    conn = ES(es_url)
    if not conn.indices.exists_index(index):
        conn.indices.create_index(index)
    return conn


def index_datasets(echo_url, es_url, index):
    """Index CKAN datasets into ElasticSearch."""

    conn = get_es_conn(es_url, index)

    page_size = 2000
    page_num = 1
    datasets = {}
    errors = {}
    while True:
        r = requests.get(echo_url, params={'page_size':page_size, 'page_num':page_num})
        page_num += 1
        r.raise_for_status()
        results = r.json()
        if len(results['feed']['entry']) == 0: break 
        for res in results['feed']['entry']:
            locations = []
            if 'boxes' in res:
                for box in res['boxes']:
                    # add GeoJSON if defined (for now only bbox)
                    lat_min, lon_min, lat_max, lon_max = box.split()
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
                    locations.append({
                        "type": "polygon",
                        "coordinates": [[
                            [ lon_min, lat_min ],
                            [ lon_min, lat_max ],
                            [ lon_max, lat_max ],
                            [ lon_max, lat_min ],
                            [ lon_min, lat_min ]
                        ]]
                    })
            elif 'points' in res:
                for point in res['points']:
                    lat, lon = point.split()
                    lat = float(lat)
                    lon = float(lon)
                    locations.append({
                        "type": "point",
                        "coordinates": [ lon, lat ]
                    })
            res['facetview_location'] = locations
          
            # index
            try: conn.index(res, index, 'echo', res['id'])
            except Exception, e:
                print("Got error: %s" % str(e))
                errors[res['id']] = res
                with open('errors/%s.json' % res['id'], 'w') as f:
                    json.dump(res, f, indent=2)
                continue
            datasets[res['id']] = True
            #print(json.dumps(res, indent=2))

    #print("\n".join(datasets))


if __name__ == "__main__":
    env = os.environ.get('CKAN_ENV', 'prod')
    app = create_app('ckan.settings.%sConfig' % env.capitalize(), env=env)
    es_url = app.config['ELASTICSEARCH_URL']
    echo_url =  app.config['ECHO_REST_URL']
    index = app.config['ECHO_ELASTICSEARCH_INDEX']

    index_datasets(echo_url, es_url, index)
