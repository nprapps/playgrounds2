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
  * Talbot Avenue Boston, MA 2124
  ! Lt Walter E Fuller Memorial Parkway New Bedford, MA 2740
  ! 34 JerdenÕs Lane Rockport, MA 1966
  * 18100 Washington Grove Lane Germantown, MD 20874
  * 75 School Street West Dennis, MA 2670
  * East Progress Street Hillman, MI 49746
  * I-075 Northbound at Mile Marker 10 Monroe, MI 48161
  * Little Neck Pkwy, 42 To 43 Aves Little Neck, NY 11363
  * INSIDE WILLOWBROOK PARK ADJ TO CAROUSEL FOR ALL CH Staten Island, NY 10314
  * 14 St, 31 Ave Astoria, NY 11106
  * 700 Main Street Oconomowoc, WI 53066
  * 5083 Colerain Avenue Cincinnati, OH 45223
  * 2310 Atascocita Road Humble, TX 77396
  * Ocean Avenue New London, CT 6320
  * Nevers Road South Windsor, CT 6074
  * 1035 Newfield Avenue Stamford, CT 6905
  * Boardwalk & Beach 59-60 Sts Arverne, NY 11692
  * Tunnel Plaza, 50 Ave, 11 St Long Island City, NY 11101
  * Cross Bay Blvd, 100 Pl, E 18 Rd, 203 Ave Far Rockaway, NY 11693
  * 2201 NW 9th Avenue Ft. Lauderdale, FL 33311
  * Rivermont Ave Lynchburg, VA 24503
  * 21 St, 45 Ave, 11 St, 45 Rd Long Island City, NY 11101
  * 91 Central Avenue Parsippany, NJ 7950
  * 11675 Hazel Dell Parkway Carmel, IN 46032
  ! 802 20th St NW Cleveland, TN 37311
  * Classon Ave, Fulton St, Irving Pl Brooklyn, NY 11238
  * Sullivan Pl W/o Nostrand Ave Brooklyn, NY 11225
  * 6003 Old Jonestown Road Harrisburg, PA 17112
  * 3500 Darby Road Haverford, PA 19041
  ! 709 Pierce Avenue Macon, GA 31204
  * Classon Ave, Sterling Pl & Park Pl Brooklyn, NY 11238
  * SEAMAN AVE BET ISHAM, W 207 ST New York, NY 10034
  * Harrison Ave Bet Walton & Lorimer Sts Brooklyn, NY 11206
  * 82 To 83 St At 18 Ave Brooklyn, NY 11214
  * S/s Jamaica Ave Bet 202 & 204 Sts Hollis, NY 11423
  * 1 ST & E RIVER Astoria, NY 11102
  * Columbia Hts, Middagh, Cranberry & Willow Sts Brooklyn, NY 11201
  * Archer Ave, 138 Pl, 91 Ave, 138 St Jamaica, NY 11435
  * 88-15 182nd Street, Queens, NY 11423 Hollis, NY 11423
  * M Garvey Blvd, Madison To Monroe Sts Brooklyn, NY 11221
  * Amsterdam Ave, W 136 St New York, NY 10031
  * Clymer St Bet Wythe And Kent Aves Brooklyn, NY 11211
  * Hope St, Marcy, Metropolitan Aves Brooklyn, NY 11211
  * 80TH ST, JUNIPER BLVD S, 77TH PLACE, JUNIPER BLVD Middle Village, NY 11379
  * Brookville Blvd, S/o 136 Ave Rosedale, NY 11422
  * COLLEGE PT BLVD, BOTANIC GDNS Flushing, NY 11355
  * S/O AVE U & E 38 ST Brooklyn, NY 11234
  * 41 To 42 Aves, 103 St Corona, NY 11368
  * Henry St, Market St, E Broadway New York, NY 10002
  * BET GRAHAM BLVD, JEFFERSON AVE Staten Island, NY 10306
  * W 166 St, Nelson Ave, Wododycrest Ave Bronx, NY 10452
  * Atlantic Ave, Columbia, State Sts , NY
  * W 26, 8 To 9 Aves New York, NY 10001
  * NEAR THE RECREATION BUILDING; OFF BAISLEY AVE Jamaica, NY 11434
  * S/s W Houston St, Ave Of Americas New York, NY 10012
  * 108-10 109 Ave, Queens, NY 11420 South Ozone Park, NY 11420
  * 85-15 143rd Street, Queens, NY 11435 Jamaica, NY 11435
  * 1919 Prospect Avenue, Bronx, NY 10457 Bronx, NY 10457
  * 178-37 146 Terrace, Queens, NY 11434 Jamaica, NY 11434
  * 57-12 94 Street , Queens, NY 11373 Elmhurst, NY 11373
  * 147-27 15th Drive, Queens, NY 11357 Whitestone, NY 11357
  * 86-50 109 Street, Queens, NY 11418 Elmhurst, NY 11373
  * 41ST RD AND 12TH ST (EAST OF VERNON BLVD) Long Island City, NY 11101
  * N/O G C PKWY OPP 193 ST Hollis, NY 11423
  * W 64 St, W/s Amsterdam Ave New York, NY 10023
  * UNION TPKE, PARK LANE S, ADJ OVERLOOK Kew Gardens, NY 11415
  * 30 To 31 Aves & Boody St, Bklyn-queens Exwy Woodside, NY 11377
  * 4 ST & PROSPECT PK W Brooklyn, NY 11215
  * 3 Ave, Nevins, Degraw & Douglas Sts Brooklyn, NY 11217
  * E 178 ST, UPPER LEVEL Bronx, NY 10457
  * Thompson St, Spring To Prince Sts New York, NY 10012
  * Vleigh Pl, 141 St & Union Tpke Flushing, NY 11367
  * 99 To 100 Sts, 3 Ave New York, NY 10029
  * WASHINGTON SQ N/EAST OF 5 AVE New York, NY 10011
  * 52 St, Woodside Ave, 39 Rd, 39 Dr, 54 St Woodside, NY 11377
  * North Avenue Elizabeth, NJ 7208
  * 4910 South Culberhouse Jonesboro, AR 72404
  * 700 West Silver Lake Drive NE Rochester, MN 55906
  * South Somerset Avenue Ventnor City, NJ 8406


Results:

  coded: 1199
  multi results: 77
  no results: 6
  written: 1199

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
