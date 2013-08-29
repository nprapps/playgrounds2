#!/usr/bin/env python

import app_config
from models import Playground

SEARCH_DISTANCE = 0.001

matched = set()

def print_playground(playground):
    print '%s: http://%s/%s/playground/%s' % (
        playground.name or 'unnamed',
        app_config.PRODUCTION_S3_BUCKETS[0],
        app_config.PROJECT_SLUG,
        playground.slug
    )

for playground in Playground.select():
    if playground.id in matched:
        continue

    lat = playground.latitude
    lng = playground.longitude

    if not lat or not lng:
        continue

    nearby = Playground.select().where(
        Playground.latitude.between(
            lat - SEARCH_DISTANCE, lat + SEARCH_DISTANCE
        ),
        Playground.longitude.between(
            lng - SEARCH_DISTANCE, lng + SEARCH_DISTANCE
        )
    )


    if nearby.count() > 1:
        print_playground(playground)

        for n in nearby:
            if n.id == playground.id:
                continue

            print_playground(n)
    
            matched.add(n.id)

        print ''
