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
            'bq': 'full_text:\'' + $search_query.val() + '\'',
        };

        var return_fields = ['name', 'latitude', 'longitude'];

        var latitude = parseFloat($search_latitude.val());
        var longitude = parseFloat($search_longitude.val());

        if (latitude) {
            // Convert to approximate meters
            var latitude_meters = parseInt(latitude * 111133);
            var longitude_meters = parseInt(longitude * Math.cos(latitude) * 111133);

            // Compile ranking algorithm
            var rank_distance = 'sqrt(pow(abs(' + latitude_meters + ' - latitude),2) + pow(abs(' + longitude_meters + ' - longitude),2))';

            params['rank'] = 'distance';
            params['rank-distance'] = rank_distance;

            return_fields.push('distance');
        }

        params['return-fields'] = return_fields.join(',')

        $.getJSON('/cloudsearch/2011-02-01/search', params, function(data) {
            _.each(data['hits']['hit'], function(hit) {
                var context = $.extend(APP_CONFIG, hit);
                var html = JST.playground_item(context);

                $search_results.empty();
                $search_results.append(html);
            });
        });

        return false;
    });
});
