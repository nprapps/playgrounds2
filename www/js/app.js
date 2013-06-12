var GEOLOCATE = Modernizr.geolocation;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 10;
var RESULTS_DEFAULT_ZOOM = 15;

var $search_form = null;
var $search_query = null;
var $search_latitude = null;
var $search_longitude = null;
var $geolocate_button = null;
var $search_results = null;
var $search_results_map_wrapper = null;
var $search_results_map = null;
var $zoom_in = null;
var $zoom_out = null;

var zoom = RESULTS_DEFAULT_ZOOM;
var crs = null;

function geolocated(position) { 
    $search_latitude.val(position.coords.latitude);
    $search_longitude.val(position.coords.longitude);
}

function degToRad(degree) {
    return degree * Math.PI / 180;
}

function radToDeg(radian) {
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

$(function() {
    $search_form = $('#search');
    $search_query = $('#search input[name="query"]');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_results = $('#search-results');
    $search_results_map_wrapper = $('#search-results-map-wrapper');
    $search_results_map = $('#search-results-map');
    $zoom_in = $('#zoom-in');
    $zoom_out = $('#zoom-out');

    var crs = L.CRS.EPSG3857;

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(geolocated);
    });

    $('#newyork').click(function() {
        $search_latitude.val(40.7142);
        $search_longitude.val(-74.0064);
    });

    $zoom_in.click(function() {
        zoom += 1;

        if (zoom == RESULTS_MAX_ZOOM) {
            $zoom_in.attr('disabled', 'disabled');
        }

        $zoom_out.removeAttr('disabled');

        $search_form.submit();
    });

    $zoom_out.click(function() {
        zoom -= 1;

        if (zoom == RESULTS_MIN_ZOOM) {
            $zoom_out.attr('disabled', 'disabled');
        }

        $zoom_in.removeAttr('disabled');

        $search_form.submit();
    });

    $search_form.submit(function() {
        var deployment_target = (APP_CONFIG.DEPLOYMENT_TARGET || 'staging');
        var query = $search_query.val();
        var latitude = parseFloat($search_latitude.val());
        var longitude = parseFloat($search_longitude.val());

        var params = {};
        var return_fields = ['name', 'city', 'state', 'latitude', 'longitude'];

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
            var rank_distance = '3958.761 * Math.acos(Math.sin(' + latitude_radians + ') * Math.sin(((latitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) + Math.cos(' + latitude_radians + ') * Math.cos(((latitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) * Math.cos((((longitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) - ' + longitude_radians + '))';

            params['rank'] = 'distance';
            params['rank-distance'] = rank_distance;

            return_fields.push('distance');
        }

        params['bq'] = '(and ' + query_bits.join(' ') + ')';
        params['return-fields'] = return_fields.join(',')

        $.getJSON('/cloudsearch/2011-02-01/search', params, function(data) {
            $search_results.empty();
            $search_results_map_wrapper.hide();

            var markers = []; 

            if (data['hits']['hit'].length > 0) {
                _.each(data['hits']['hit'], function(hit, i) {
                    var context = $.extend(APP_CONFIG, hit);
                    var html = JST.playground_item(context);

                    $search_results.append(html);

                    if (hit.data.latitude.length > 0) {
                        markers.push('pin-m-' + i + '+ff6633(' + cloudSearchToDeg(hit.data.longitude[0]) + ',' + cloudSearchToDeg(hit.data.latitude[0]) + ')');
                    }
                });
            } else {
                $search_results.append('<li>No results</li>');
            }

            markers.push('pin-l-star+ff6633(' + longitude + ',' + latitude + ')');

            if (latitude && markers.length > 0) {
                $search_results_map.attr('src', 'http://api.tiles.mapbox.com/v3/examples.map-4l7djmvo/' + markers.join(',') + '/' + longitude + ',' + latitude + ',' + zoom + '/' + RESULTS_MAP_WIDTH + 'x' + RESULTS_MAP_HEIGHT + '.png');

                $search_results_map_wrapper.show();
            }
        });

        return false;
    });

    /*if (Modernizr.geolocation) {
        $geolocate_button.show();
    }*/
});
