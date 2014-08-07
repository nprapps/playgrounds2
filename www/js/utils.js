var RESULTS_DEFAULT_ZOOM = APP_CONFIG.RESULTS_DEFAULT_ZOOM;

function coordinatesApproxEqual(ll1, ll2, accuracy) {
    /*
     * Check if coordinates are the same within a tenth of a degree
     *  in both dimensions. (or some other accuracy)
     */
    if (_.isUndefined(accuracy)) {
        accuracy = 10;
    }

    return (Math.round(ll1.lat() * accuracy) / accuracy == Math.round(ll2.lat() * accuracy) / accuracy &&
        Math.round(ll1.lng() * accuracy) / accuracy == Math.round(ll2.lng() * accuracy) / accuracy);
}

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

function degToCloudSearch(degree) {
    /*
     * Convert a degree of lat or lon to our CloudSearch uint representation.
     */
    return parseInt((degree + APP_CONFIG.CLOUD_SEARCH_DEG_OFFSET) * APP_CONFIG.CLOUD_SEARCH_DEG_SCALE);
}

function cloudSearchToDeg(uint) {
    /*
     * Convert a CloudSearch uint into a degree of lat or lon.
     */
    return parseFloat((uint / APP_CONFIG.CLOUD_SEARCH_DEG_SCALE) - APP_CONFIG.CLOUD_SEARCH_DEG_OFFSET);
}

function buildCloudSearchParams(latitude, longitude, zoom, query) {
    /*
     * Reads the current state of the UI and builds appropraite CloudSearch query params.
     */
    var deployment_target = (APP_CONFIG.DEPLOYMENT_TARGET || 'staging');
    var params = {};
    var return_fields = ['display_name', 'city', 'state', 'latitude', 'longitude', 'slug'];

    for (feature in window.FEATURES) {
        return_fields.push('feature_' + feature.replace(/-/g, '_'));
    }

    var query_bits = ['deployment_target:\'' + deployment_target + '\''];

    /*if (query) {
        query_bits.push('full_text:\'' + query + '\'');
    }*/

    // If using geosearch
    if (latitude) {
        // Generate bounding box for map viewport
        var crs = L.CRS.EPSG3857;
        var point = crs.latLngToPoint(new L.LatLng(latitude, longitude), zoom);
        var upper_left = point.subtract([RESULTS_MAP_WIDTH / 2, RESULTS_MAP_HEIGHT / 2]);
        var lower_right = point.add([RESULTS_MAP_WIDTH / 2, RESULTS_MAP_HEIGHT / 2]);
        var northwest = crs.pointToLatLng(upper_left, zoom);
        var southeast = crs.pointToLatLng(lower_right, zoom);

        query_bits.push('longitude:' + degToCloudSearch(northwest.lng) + '..' + degToCloudSearch(southeast.lng) + ' latitude:' + degToCloudSearch(southeast.lat) + '..' + degToCloudSearch(northwest.lat));

        var latitude_radians = degToRad(latitude);
        var longitude_radians = degToRad(longitude);
        var offset = APP_CONFIG.CLOUD_SEARCH_DEG_OFFSET;
        var scale = APP_CONFIG.CLOUD_SEARCH_DEG_SCALE;

        var sin_latitude = Math.sin(latitude_radians);
        var cos_latitude = Math.cos(latitude_radians);
        var pi_over_180 = 3.14159 / 180;
        var earth_radius_miles = 3958.761;
        var coefficient = earth_radius_miles * 1000;

        // Points in the index have been scaled and offset
        var that_latitude = '(((latitude / ' + scale + ') - ' + offset + ') * ' + pi_over_180 + ')';
        var that_longitude = '(((longitude / ' + scale + ') - ' + offset + ') * ' + pi_over_180 + ')';

        // Compile ranking algorithm (spherical law of cosines)
        // Note results are scaled up by 10000x.
        var rank_distance = coefficient + ' * Math.acos(' + sin_latitude + ' * Math.sin(' + that_latitude + ') + ' + cos_latitude + ' * Math.cos(' + that_latitude + ') * Math.cos((' + that_longitude + ') - ' + longitude_radians + '))';

        //var x = (lon2-lon1) * Math.cos((lat1+lat2)/2);
        //var y = (lat2-lat1);
        //var d = Math.sqrt(x*x + y*y) * R;

        // Alternate Equirectangular distance (should be faster, but not working)
        //var x = '(' + that_longitude + ' - ' + longitude_radians + ') * Math.cos((' + that_latitude + ' + ' + latitude_radians + ') / 2)';
        //var y = '(' + that_latitude + ' - ' + latitude_radians + ')';
        //var rank_distance = 'Math.sqrt(Math.pow(' + x + ', 2) + Math.pow(' + y + ', 2)) * ' + coefficient;

        params['rank'] = 'distance';
        params['rank-distance'] = rank_distance;
        params['size'] = '26';  // We never need more than 26 results

        return_fields.push('distance');
    } else {
        params['rank'] = 'name';
    }

    params['bq'] = '(and ' + query_bits.join(' ') + ')';
    params['return-fields'] = return_fields.join(',');
    params['size'] = 26;

    return params;
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

function require_us_address(address_components) {
    address_components.forEach(function(address) {
        if (address['types'][0] == 'country' && address['long_name'] !== 'United States') {
            make_alert('Please choose an address within the United States.', 'warning', 'div.alerts');
        };
    });
};

function prevent_body_scroll(e) {
    if (!$('.scrollable').has($(e.target)).length) {
        e.preventDefault();
    }
}

function make_alert(text, klass, target_element){
    // Generate a template.
    var alert_template = _.template('<div class="alert <%= klass %>"><%= text %></div>');

    // Blank the div and add our rendered template.
    $(target_element).html(
        alert_template({
            'text': text,
            'klass': klass
        })
    ).hide().slideDown();

    // Make it disappear
    setTimeout(function() {
        $(target_element).slideUp();
    }, 5000);
}

function set_driving_urls(){
    var $directions_wrapper = $('.directions-wrapper');
    var $directions_link = $('#directions-link');
    var directions_header = $('<h5>Get Directions</h5>');
    var $google_maps_link = $('<a class="btn btn-blue"><i class="icon icon-google-plus"></i>Google Maps</a>');

    $directions_link.attr('href', $directions_link.data('ios-map'));
    $directions_link.html('<i class="icon icon-apple"></i> Apple Maps');

    $directions_link.parent().before(directions_header);
    $directions_link.after($google_maps_link);

    $('div.address').addClass('apps');

    $google_maps_link.on('click', function(){
        var now = new Date().valueOf();
        setTimeout(function(){
            if (new Date().valueOf() - now > 500) return;
            if(confirm('Google Maps is not installed. Tap "okay" to go to the App Store.')){
              document.location = 'https://itunes.apple.com/us/app/google-maps/id585027354?mt=8';
            }
        }, 25);
        document.location = $directions_link.data('ios-gmap');
    });
}

$(function(){
    if (navigator.userAgent.match(/iPhone|iPad|iPod/i)){
        set_driving_urls();
    }
});
