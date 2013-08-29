#!/usr/bin/env python

import app_config
from models import Playground

SEARCH_DISTANCE = 0.001

for playground in Playground.select():
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
        print playground.name

        for n in nearby:
            if n.id == playground.id:
                continue

            print '  %s: http://%s/%s/playground/%s' % (
                n.name or 'unnamed',
                app_config.PRODUCTION_S3_BUCKETS[0],
                app_config.PROJECT_SLUG,
                n.slug
            )
