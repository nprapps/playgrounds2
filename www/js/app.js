var GEOLOCATE = Modernizr.geolocation;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 8;
var RESULTS_DEFAULT_ZOOM = 14;

var LETTERS = 'abcdefghijklmnopqrstuvwxyz';

var $search_title = null;
var $search_form = null;
var $search_address = null;
var $search_again = null;
var $search_divider = null;
var $search_query = null;
var $search_latitude = null;
var $search_longitude = null;
var $geolocate_button = null;
var $search_results_wrapper = null;
var $search_results = null;
var $search_results_map_wrapper = null;
var $search_results_map = null;
var $search_results_map_loading = null;
var $zoom_in = null;
var $zoom_out = null;
var $search_help = null;
var $search_help_us = null;
var $did_you_mean = null;
var $results_address = null;
var $no_geocode = null;
var $results_loading = null;

var is_index = false;
var is_playground = false;

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
    var return_fields = ['name', 'display_name', 'city', 'state', 'latitude', 'longitude', 'public_remarks', 'slug'];

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

    $search_results.empty();
    $search_results_map_loading.show();
    $search_results_map.css('opacity', '0.25');

    $.ajax({
        url: APP_CONFIG.CLOUD_SEARCH_PROXY_BASE_URL + '/cloudsearch/2011-02-01/search',
        data: buildCloudSearchParams(),
        dataType: 'jsonp',
        success: function(data) {
            $results_loading.hide();

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

                $search_results_map.on('load', function() {
                    $search_results_map_loading.hide();
                    $search_results_map.css('opacity', '1.0');

                    $search_results_map.off('load');
                });

                $search_results_map.attr('src', 'http://api.tiles.mapbox.com/v3/' + APP_CONFIG.MAPBOX_BASE_LAYER + '/' + markers.join(',') + '/' + longitude + ',' + latitude + ',' + zoom + '/' + RESULTS_MAP_WIDTH + 'x' + RESULTS_MAP_HEIGHT + '.png');

                $search_results_map_wrapper.show();
                $results_address.show();
            }

            $search_results.show();
        },
        cache: true,
        jsonp: false,
        jsonpCallback: 'myCallback'
    });

    hide_search();
}

function reset_zoom() {
    zoom = RESULTS_DEFAULT_ZOOM;
    $zoom_in.removeAttr('disabled');
    $zoom_out.removeAttr('disabled');
}

function show_search() {
    $search_form.show();
    $search_results_wrapper.hide();
    $search_again.hide();
    $search_title.show();
}

function hide_search() {
    $search_form.hide();
    $search_again.show();
}

$(function() {
    $search_title = $('#search-title');
    $search_form = $('#search');
    $search_address = $('#search input[name="address"]');
    $search_again = $('#search-again');
    $search_divider = $search_form.find('h6.divider');
    $search_query = $('#search input[name="query"]');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_results_wrapper = $('#search-results-wrapper');
    $search_results = $('#search-results');
    $search_results_map_wrapper = $('#search-results-map-wrapper');
    $search_results_map = $('#search-results-map');
    $search_results_map_loading = $('#search-results-map-loading');
    $zoom_in = $('#zoom-in');
    $zoom_out = $('#zoom-out');
    $search_help = $('#search-help');
    $did_you_mean = $('#search-help ul');
    $search_help_us = $('#search-help-prompt');
    $results_address = $('#results-address');
    $no_geocode = $('#no-geocode');
    $results_loading = $('#results-loading');

    is_index = $('body').hasClass('index');
    is_playground = $('body').hasClass('playground');

    if (is_index) {
        crs = L.CRS.EPSG3857;
    }

    /* THE THANK YOU MESSAGE BLOCK */

    // This is a function from the internet for parsing the URL location.
    // Returns undefined if the key doesn't exist; returns the value if it does.
    function getURLParameter(name) {
        return decodeURI(
            (RegExp(name + '=' + '(.+?)(&|$)').exec(location.search)||[null])[1]
        );
    }

    // This is the part that Danny or Aly will be making do something interesting.
    // COPYTEXT[message] will contain the message from the copy spreadsheet.
    function writeMessage(message) {
        alert(message);
    }

    // Fetches the key from the URL. This could easily be undefined or null.
    var action = getURLParameter('action');

    // If the URL parameter doesn't exist or is blank, don't do anything.
    // If it does exist, pass to write_message.
    // This block handles looking up the key from the URL and the message from the copy text.
    if ((action !== "undefined") && (action !== null)) {
        // Look up the message in the copy text.
        var message = COPYTEXT[message];

        // Only if the message exists should writeMessage() get called.
        if ((message !== "undefined") && (message !== null)) {
            writeMessage(message);
        }
    }

    $geolocate_button.click(function() {
        reset_zoom();
        navigator.geolocation.getCurrentPosition(function(position) {
            hide_search();
            $search_help.hide();
            $search_results.empty();
            $search_results_map_wrapper.hide();
            $results_address.hide();
            $search_results_wrapper.show();

            $results_address.text('Showing results near you.');

            $search_latitude.val(position.coords.latitude);
            $search_longitude.val(position.coords.longitude);
            $results_loading.show();
            search();
        });
        $results_address.html('Showing results nearby');
    });

    $('#newyork').click(function() {
        $search_query.val('');
        $search_address.val('New York City, New York');
        $search_form.submit();
    });
    $('#huntley').click(function() {
        $search_query.val('');
        $search_address.val('Deicke Park, Huntley, Illinois');
        $search_form.submit();
    });
    $('#zip').click(function() {
        $search_query.val('');
        $search_address.val('79410');
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
        $results_address.html('Showing results near ' + address);

        $search_help.hide();
        $search_help_us.show();

        $results_loading.show();
        search();
    });

    $search_again.on('click', function() {
        show_search();
    });

    $search_form.submit(function() {
        reset_zoom();
        hide_search();
        $search_help.hide();
        $search_results.empty();
        $search_results_map_wrapper.hide();
        $results_address.hide();
        $no_geocode.hide();
        $search_results_wrapper.show();

        var address = $search_address.val();

        if (address) {
            $results_loading.show();

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

                    $results_loading.hide();

                    if (locales.length == 0) {
                        $did_you_mean.append('<li>No results</li>');

                        $no_geocode.show();
                    } else if (locales.length == 1) {
                        var locale = locales[0];

                        $search_latitude.val(locale['latLng']['lat']);
                        $search_longitude.val(locale['latLng']['lng']);

                        $results_address.html('Showing results near ' + formatMapQuestAddress(locale));

                        $results_loading.show();
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
                        $search_help_us.hide();
                    }
                }
            });
        } else {
            $search_latitude.val('');
            $search_longitude.val('');
            $results_loading.show();
            search();
        }
        return false;
    });

    if (GEOLOCATE) {
        $geolocate_button.show();
        $search_divider.show();
    }

    if (is_playground) {
        $('.playground-features i').tooltip( { trigger: 'click' } );
    }
});
