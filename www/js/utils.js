function degToRad(degree) {
    /*
     * Convert degrees to radians.
     */
    return degree * Math.PI / 180;
}

function radToDeg(radian) {
    /*
     * Convert radians to degrees.
     */
    return radian / Math.PI * 180;
}

function formatMapQuestAddress(locale) {
    var quality = locale['geocodeQuality'];
    var street = locale['street'];
    var city = locale['adminArea5'];
    var state = locale['adminArea3'];
    var county = locale['adminArea4'];
    var zip = locale['postalCode'];

    if (quality == 'POINT' || quality == 'ADDRESS' || quality == 'INTERSECTION') {
        return street + ' ' + city + ', ' + state + ' ' +  zip;
    } else if (quality == 'CITY') {
        return city + ', ' + state;
    } else if (quality == 'COUNTY') {
        return county + ' County, ' + state;
    } else if (quality == 'ZIP' || quality == 'ZIP_EXTENDED') {
        return zip + ', ' + state;
    } else if (quality == 'STATE') {
        return state;
    } else {
        return '';
    }
}


function geocode(address_string, callback) {
    $.ajax({
        'url': 'http://open.mapquestapi.com/geocoding/v1/?inFormat=kvp&location=' + address_string,
        'dataType': 'jsonp',
        'contentType': 'application/json',
        'success': function(data) {
            var locales = data['results'][0]['locations'];
            var locale = locales[0];
            var zip_list = [];

            callback(locale);
        }
    });
}

function reverseGeocode(latitude, longitude, callback) {
    $.ajax({
        'url': 'http://open.mapquestapi.com/geocoding/v1/reverse',
        'data': { 'location': latitude + ',' + longitude },
        'dataType': 'jsonp',
        'contentType': 'application/json',
        'success': function(data) {
            var locales = data['results'][0]['locations'];
            var locale = locales[0];
            var zip_list = [];

            if (locale['adminArea4'] == 'District of Columbia')  {
                locale['adminArea5'] = 'Washington';
                locale['adminArea3'] = 'District of Columbia';
            }

            callback(locale);
        }
    });
}