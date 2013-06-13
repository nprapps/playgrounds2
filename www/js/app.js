var GEOLOCATE = Modernizr.geolocation;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 8;
var RESULTS_DEFAULT_ZOOM = 14;

var LETTERS = 'abcdefghijklmnopqrstuvwxyz';

var $search_form = null;
var $search_address = null;
var $search_query = null;
var $search_latitude = null;
var $search_longitude = null;
var $geolocate_button = null;
var $search_results = null;
var $search_results_map_wrapper = null;
var $search_results_map = null;
var $zoom_in = null;
var $zoom_out = null;
var $search_help = null;
var $did_you_mean = null;
var $results_address = null;

var zoom = RESULTS_DEFAULT_ZOOM;
var crs = null;

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

function buildCloudSearchParams() {
    /*
     * Reads the current state of the UI and builds appropraite CloudSearch query params.
     */
    var deployment_target = (APP_CONFIG.DEPLOYMENT_TARGET || 'staging');
    var query = $search_query.val();
    var latitude = parseFloat($search_latitude.val());
    var longitude = parseFloat($search_longitude.val());

    var params = {};
    var return_fields = ['name', 'display_name', 'city', 'state', 'latitude', 'longitude'];

    var query_bits = ['deployment_target:\'' + deployment_target + '\''];

    if (query) {
        query_bits.push('full_text:\'' + query + '\'');
    }

    // If using geosearch
    if (latitude) {
        // Generate bounding box for map viewport
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

        // Compile ranking algorithm (spherical law of cosines)
        // Note results are scaled up by 1000x.
        var rank_distance = '3958.761 * Math.acos(Math.sin(' + latitude_radians + ') * Math.sin(((latitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) + Math.cos(' + latitude_radians + ') * Math.cos(((latitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) * Math.cos((((longitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) - ' + longitude_radians + ')) * 1000';

        params['rank'] = 'distance';
        params['rank-distance'] = rank_distance;

        return_fields.push('distance');
    } else {
        params['rank'] = 'name';
    }

    params['bq'] = '(and ' + query_bits.join(' ') + ')';
    params['return-fields'] = return_fields.join(',')

    return params;
}

function buildMapboxPin(size, shape, color, lat, lng) {
    /*
     * Generate the URL format for a mapbox static pin.
     */
    return 'pin-' + size + '-' + shape + '+' + color + '(' + lng + ',' + lat + ')';
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

function search() {
    /*
     * Execute a search using current UI state.
     */
    var latitude = parseFloat($search_latitude.val());
    var longitude = parseFloat($search_longitude.val());

    $.getJSON('/cloudsearch/2011-02-01/search', buildCloudSearchParams(), function(data) {
        $search_results.empty();

        var markers = []; 

        if (data['hits']['hit'].length > 0) {
            _.each(data['hits']['hit'], function(hit, i) {
                var context = $.extend(APP_CONFIG, hit);
                context['letter'] = LETTERS[i];

                var html = JST.playground_item(context);

                $search_results.append(html);

                if (hit.data.latitude.length > 0) {
                    var lat = cloudSearchToDeg(hit.data.latitude[0]);
                    var lng = cloudSearchToDeg(hit.data.longitude[0]);

                    markers.push(buildMapboxPin('m', context['letter'], 'ff6633', lat, lng));
                }
            });
        } else {
            $search_results.append('<li class="no-results">No results</li>');
        }

        if (latitude) {
            markers.push(buildMapboxPin('l', 'circle', '006633', latitude, longitude));

            $search_results_map.attr('src', 'http://api.tiles.mapbox.com/v3/' + APP_CONFIG.MAPBOX_BASE_LAYER + '/' + markers.join(',') + '/' + longitude + ',' + latitude + ',' + zoom + '/' + RESULTS_MAP_WIDTH + 'x' + RESULTS_MAP_HEIGHT + '.png');

            $search_results_map_wrapper.show();
        }
        $search_results.show();
    });
}

$(function() {
    $search_form = $('#search');
    $search_address = $('#search input[name="address"]');
    $search_query = $('#search input[name="query"]');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_results = $('#search-results');
    $search_results_map_wrapper = $('#search-results-map-wrapper');
    $search_results_map = $('#search-results-map');
    $zoom_in = $('#zoom-in');
    $zoom_out = $('#zoom-out');
    $search_help = $('#search-help');
    $did_you_mean = $('#search-help ul');
    $results_address = $('#results-address');

    crs = L.CRS.EPSG3857;

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(function(position) {
            $search_latitude.val(position.coords.latitude);
            $search_longitude.val(position.coords.longitude);
            $search_form.submit();
        });
    });

    $('#newyork').click(function() {
        $search_query.val('');
        $search_address.val('');
        $search_latitude.val(40.7142);
        $search_longitude.val(-74.0064);
        $results_address.html('Showing results near New York, NY.');
        $search_form.submit();
    });
    $('#huntley').click(function() {
        $search_query.val('');
        $search_address.val('');
        $search_latitude.val(42.163924);
        $search_longitude.val(-88.433642);
        $results_address.html('Showing results near Huntley, IL.');
        $search_form.submit();
    });
    $('#zip').click(function() {
        $search_query.val('');
        $search_address.val('');
        $search_latitude.val(33.568778);
        $search_longitude.val(-101.890443);
        $results_address.html('Showing results near 79410, TX.');
        $search_form.submit();
    });

    $zoom_in.click(function() {
        zoom += 1;

        if (zoom == RESULTS_MAX_ZOOM) {
            $zoom_in.attr('disabled', 'disabled');
        }

        $zoom_out.removeAttr('disabled');

        search();
    });

    $zoom_out.click(function() {
        zoom -= 1;

        if (zoom == RESULTS_MIN_ZOOM) {
            $zoom_out.attr('disabled', 'disabled');
        }

        $zoom_in.removeAttr('disabled');

        search();
    });

    $did_you_mean.on('click', 'li', function() {
        var $this = $(this);
        var address = $this.data('address');
        var latitude = $this.data('latitude');
        var longitude = $this.data('longitude');

        $search_latitude.val(latitude);
        $search_longitude.val(longitude);
        $results_address.html('Showing results near ' + address + '.');

        $search_help.hide();
        
        search();
    });

    $search_form.submit(function() {
        $search_help.hide();
        $search_results.empty();
        $search_results_map_wrapper.hide();

        var address = $search_address.val();
        
        if (address) {
            $.ajax({
                'url': 'http://open.mapquestapi.com/geocoding/v1/address',
                'data': { 'location': address },
                'dataType': 'jsonp',
                'contentType': 'application/json',
                'success': function(data) {
                    var locales = data['results'][0]['locations'];

                    locales = _.filter(locales, function(locale) {
                        return locale['adminArea1'] == 'US';
                    });

                    if (locales.length == 0) {
                        $did_you_mean.append('<li>No results</li>');
                    } else if (locales.length == 1) {
                        var locale = locales[0];

                        $search_latitude.val(locale['latLng']['lat']);
                        $search_longitude.val(locale['latLng']['lng']);

                        $results_address.html('Showing results near ' + formatMapQuestAddress(locale) + '.');

                        search();
                    } else {
                        $did_you_mean.empty();

                        _.each(locales, function(locale) {
                            var context = $.extend(APP_CONFIG, locale);
                            context['address'] = formatMapQuestAddress(locale);

                            var html = JST.did_you_mean_item(context);

                            $did_you_mean.append(html);

                        });

                        $search_help.show();
                    }
                }
            });
        } else {
            search();
        }
        return false;
    });

    if (GEOLOCATE) {
        $geolocate_button.show();
    }
});
