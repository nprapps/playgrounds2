var $search_form = null;
var $search_query = null;
var $search_results = null;

$(function() {
    $search_form = $('#search');
    $search_query = $('#search input[name="query"]');
    $search_results = $('#search-results');

    $search_form.submit(function() {
        // TKTK - Hardcoded to Tyler
        var latitude = 32.3511;
        var longitude = 95.3008;

        // Convert to approximate meters
        var latitude_meters = parseInt(latitude * 111133);
        var longitude_meters = parseInt(longitude * Math.cos(latitude) * 111133);

        // Compile ranking algorithm
        var rank_distance = 'sqrt(pow(abs(' + latitude_meters + ' - latitude),2) + pow(abs(' + longitude_meters + ' - longitude),2))';

        var params = {
            'q': $search_query.val(),
            'return-fields': ['name', 'latitude'].join(','),
            'rank': 'distance',
            'rank-distance': rank_distance
        };

        $.getJSON('/cloudsearch/2011-02-01/search', params, function(data) {
            _.each(data['hits']['hit'], function(hit) {
                var context = $.extend(APP_CONFIG, hit);
                var html = JST.playground_item(context);

                $search_results.append(html);
            });
        });

        return false;
    });
});
