import time

from models import Playground
from geopy import geocoders

p = Playground.select().where(Playground.longitude >> None)
g = geocoders.GoogleV3()

success = 0
error = 0

for playground in p:
    time.sleep(0.25)

    try:
        place, (lat, lng) = g.geocode('%s %s %s %s' % (playground.address, playground.city, playground.state, playground.zip_code))
        print place, lat, lng
        success += 1

    except:
        print '\t%s %s %s %s' % (playground.address, playground.city, playground.state, playground.zip_code)
        error += 1

    playground.latitude = lat
    playground.longitude = lng
    playground.save()

print success, error
