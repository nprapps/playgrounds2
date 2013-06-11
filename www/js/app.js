var $search_form = null;
var $search_query = null;
var $search_latitude = null;
var $serach_longitude = null;
var $search_results = null;

$(function() {
    $search_form = $('#search');
    $search_query = $('#search input[name="query"]');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $search_results = $('#search-results');

    $search_form.submit(function() {
        var params = {
            'bq': 'full_text:\'' + ($search_query.val() || '-nprapps') + '\'',
        };

        var return_fields = ['name', 'city', 'state', 'latitude', 'longitude'];

        var latitude = parseFloat($search_latitude.val());
        var longitude = parseFloat($search_longitude.val());

        if (latitude) {
            // Convert to approximate meters
            var latitude_radians = Math.abs(latitude * Math.PI / 180); 
            var longitude_radians = Math.abs(longitude * Math.PI / 180);
            var scale = APP_CONFIG.CLOUD_SEARCH_RADIANS_SCALE;

            // Compile ranking algorithm
            var rank_distance = '6371 * Math.acos(Math.sin(' + latitude_radians + ') * Math.sin(latitude / ' + scale + ') + Math.cos(' + latitude_radians + ') * Math.cos(latitude / ' + scale + ') * Math.cos((longitude / ' + scale + ') - ' + longitude_radians + '))';

            params['rank'] = 'distance';
            params['rank-distance'] = rank_distance;

            return_fields.push('distance');
        }

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
});
