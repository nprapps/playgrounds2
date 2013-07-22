import csv
import time

from models import Playground
from geopy import geocoders

g = geocoders.GoogleV3()
# bing = geocoders.Bing()

error = 0
coded_goog = 0
coded_bing = 0
written = 0
# uhoh = 0

with open('data/playgrounds.csv', 'r+b') as readfile:
    read_csv = csv.reader(readfile)

    with open('data/playgrounds_geocoded.csv', 'w+b') as writefile:
        write_csv = csv.writer(writefile)

        for playground in Playground.select().where(Playground.latitude >> None):
            time.sleep(0.25)

            hard_address = '%s %s, %s %s' % (
                playground.address, 
                playground.city, 
                playground.state, 
                playground.zip_code
            )

            print (hard_address)

            try:
                place, (lat, lng) = goog.geocode(hard_address)
                playground.latitude = lat
                playground.longitude = lng
                playground.save()
                coded_goog += 1
                for row in read_csv:
                    if str(row[0]) == str(playground.id):
                        row[9] = playground.latitude
                        row[10] = playground.longitude
                        write_csv.writerow(row)
                        written += 1
                        break
                # else:
                #     uhoh += 1

            except:
                print '\t' + hard_address
                error += 1

print "coded: " + str(coded)
print "errors: " + str(error)
print "written: " + str(written)
# print "unmatched: " + str(uhoh)
