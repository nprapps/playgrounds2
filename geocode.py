import csv
import time

from models import Playground
import geopy
from geopy import geocoders

g = geocoders.GoogleV3()

error = 0
none_error = 0
coded_goog = 0
written = 0

GQueryError = geopy.geocoders.googlev3.GQueryError

"""
Bad Addresses
  ~11 of these have been fixed in playgrounds_geocoded. 
  The rest are corrupted

  * = Multiple addresses returned
  ! = No addresses returned

* 3245 North Meridian Road Meridian, ID 83642
* 6501 West 21st Street North Wichita, KS 67212
! 2801 Park Avenue Paducah, KY 42001
! 900 Lakeshore Drive Lake Charles, LA 70601
! 34 Jerdens Lane Rockport, MA 1966
* 18100 Washington Grove Lane Germantown, MD 20874
* 75 School Street West Dennis, MA 2670
* 700 Main Street Oconomowoc, WI 53066
* 5083 Colerain Avenue Cincinnati, OH 45223
* 2310 Atascocita Road Humble, TX 77396
* 1035 Newfield Avenue Stamford, CT 6905
* 2201 NW 9th Avenue Ft. Lauderdale, FL 33311
* Rivermont Ave Lynchburg, VA 24503
* 91 Central Avenue Parsippany, NJ 7950
* 11675 Hazel Dell Parkway Carmel, IN 46032
! 802 20th St NW Cleveland, TN 37311
* 6003 Old Jonestown Road Harrisburg, PA 17112
* 3500 Darby Road Haverford, PA 19041
! 709 Pierce Avenue Macon, GA 31204
* Atlantic Ave, Columbia, State Sts , NY
* 4910 South Culberhouse Jonesboro, AR 72404
* 700 West Silver Lake Drive NE Rochester, MN 55906

Results:

17 Multi addresses
5 No addresses
22 Total errors

460 non-repeating playgrounds with null latitude

TODO:

Write geocoded addresses to spreadsheet. Cannot match to read_csv;
data.py removes duplicate playgrounds. Use playground.name? New CSV?
"""

with open('data/playgrounds.csv', 'r+b') as readfile:
    read_csv = csv.reader(readfile)

    with open('data/playgrounds_geocoded.csv', 'w+b') as writefile:
        write_csv = csv.writer(writefile)

        for playground in Playground.select():
            time.sleep(0.25)

            hard_address = '%s %s, %s %s' % (
                playground.address, 
                playground.city, 
                playground.state, 
                playground.zip_code
            )

            try:
                place, (lat, lng) = g.geocode(hard_address)
                playground.latitude = lat
                playground.longitude = lng
                playground.save()
                coded_goog += 1
                for row in read_csv:
                    if row[21] == 'TRUE':
                        continue

                    row[9] = playground.latitude
                    row[10] = playground.longitude
                    write_csv.writerow(row)
                    written += 1
                    break

            except ValueError:
                print '\t*' + hard_address
                error += 1
            except GQueryError:
                print '\t!' + hard_address
                none_error += 1

print "coded: " + str(coded_goog)
print "multi results: " + str(error)
print "no results: " + str(none_error)
print "written: " + str(written)
