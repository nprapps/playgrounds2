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

function get_parameter_by_name(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
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

function require_us_address(locale) {
    var country = locale[6];
    if (country !== 'US') {
        console.log("Please provide an address located within the United States.");
    }
}

function prevent_body_scroll(e) {
    if (!$('.scrollable').has($(e.target)).length) e.preventDefault();
}