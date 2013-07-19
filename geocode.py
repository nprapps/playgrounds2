import csv
import time

from models import Playground
from geopy import geocoders

g = geocoders.GoogleV3()

error = 0
coded = 0

with open('data/playgrounds.csv', 'r+b') as readfile:
    read_csv = csv.reader(readfile)

    with open('data/playgrounds_geocoded.csv', 'w+b') as writefile:
        write_csv = csv.writer(writefile)

        for playground in Playground.select().where(Playground.latitude >> None or Playground.longitude >> None):
            time.sleep(0.25)

            try:
                place, (lat, lng) = g.geocode('%s %s %s %s' % (playground.address, playground.city, playground.state, playground.zip_code))
                coded += 1

            except:
                print '\t%s %s %s %s' % (playground.address, playground.city, playground.state, playground.zip_code)
                error += 1

            playground.latitude = lat
            playground.longitude = lng
            playground.save()

            for row in read_csv:
                if row[1] == playground.name:
                    row[9] = lat
                    row[10] = lng

                write_csv.writerow(row)

print coded
print error
