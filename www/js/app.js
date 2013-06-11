var $search_form = null;
var $search_query = null;
var $search_latitude = null;
var $search_longitude = null;
var $geolocate_button = null;
var $search_results = null;

function geolocated(position) { 
    $search_latitude.val(position.coords.latitude);
    $search_longitude.val(position.coords.longitude);
}

$(function() {
    $search_form = $('#search');
    $search_query = $('#search input[name="query"]');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_results = $('#search-results');

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(geolocated);
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
            //var bounding_box = [];

            // query_bits.push();

            var latitude_radians = Math.abs(latitude * Math.PI / 180); 
            var longitude_radians = Math.abs(longitude * Math.PI / 180);
            var scale = APP_CONFIG.CLOUD_SEARCH_FLOAT_SCALE;

            // Compile ranking algorithm (spherical law of cosines)
            var rank_distance = '3958.761 * Math.acos(Math.sin(' + latitude_radians + ') * Math.sin((latitude / ' + scale + ') * 3.14159 / 180) + Math.cos(' + latitude_radians + ') * Math.cos((latitude / ' + scale + ') * 3.14159 / 180) * Math.cos(((longitude / ' + scale + ') * 3.14159 / 180) - ' + longitude_radians + '))';

            params['rank'] = 'distance';
            params['rank-distance'] = rank_distance;

            return_fields.push('distance');
        }

        params['bq'] = '(and ' + query_bits.join(' ') + ')';
        params['return-fields'] = return_fields.join(',')

        $.getJSON('/cloudsearch/2011-02-01/search', params, function(data) {
            $search_results.empty();

            _.each(data['hits']['hit'], function(hit) {
                var context = $.extend(APP_CONFIG, hit);
                var html = JST.playground_item(context);

                $search_results.append(html);
            });
        });

        return false;
    });

    /*if (Modernizr.geolocation) {
        $geolocate_button.show();
    }*/
});
