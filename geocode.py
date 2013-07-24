import csv
import time

from models import Playground
import geopy
from geopy import geocoders

g = geocoders.GoogleV3()

error = 0
none_error = 0
coded = 0
written = 0

with open('data/playgrounds.csv', 'r+b') as readfile:
    with open('data/playgrounds_geocoded.csv', 'wb') as writefile:
        read_csv = csv.reader(readfile)
        row0 = read_csv.next()
        row0.append('GEOCODE-ERROR')
        row0 = tuple(row0)
        write_csv = csv.DictWriter(writefile, fieldnames=row0, delimiter=',')
        write_csv.writeheader()

        for playground in Playground.select():
            time.sleep(0.25)

            hard_address = '%s %s, %s %s' % (
                playground.address, 
                playground.city, 
                playground.state, 
                playground.zip_code
            )

            for row in read_csv:
                if row[21] == 'TRUE':
                    continue
                try:
                    place, (lat, lng) = g.geocode(hard_address)
                except:
                    row.append('TRUE')
                    write_csv.writerow(dict(zip(row0,row)))
                    continue

                playground.latitude = lat
                playground.longitude = lng
                playground.save()
                coded += 1
                
                row[9] = '%s' % playground.latitude
                row[10] = '%s' % playground.longitude
                row.append('FALSE')
                write_csv.writerow(dict(zip(row0,row)))
                written += 1
                continue

print "coded: " + str(coded)
print "written: " + str(written)
