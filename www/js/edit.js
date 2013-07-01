var $edit_map = null;
var $address = null;
var $search_address = null;
var $search_help = null;
var $did_you_mean = null;
var $no_geocode = null;
var $results_loading = null;

$(function() {
    $address = $('#address');
    $search_address = $('#search-address');
    $search_help = $('#search-help');
    $did_you_mean = $('#search-help ul');
    $no_geocode = $('#no-geocode');
    $results_loading = $('#results-loading');

    map = L.map('edit-map').setView([38.9, -77], 7);
    map_layer = L.mapbox.tileLayer('geraldrich.map-wow338yo', {
        detectRetina: true,
        retinaVersion: 'geraldrich.map-y6mt2diq'
    }).addTo(map);
    grid_layer = L.mapbox.gridLayer('geraldrich.map-wow338yo').addTo(map);
    map.addControl(L.mapbox.gridControl(grid_layer));

    $search_address.click(function() {
        var address = $address.val();
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

                        // $search_latitude.val(locale['latLng']['lat']);
                        // $search_longitude.val(locale['latLng']['lng']);
                        console.log('Found it');

                        // $results_address.html('Showing results near ' + formatMapQuestAddress(locale));

                        $results_loading.show();
                    } else {
                        $did_you_mean.empty();

                        _.each(locales, function(locale) {
                            var context = $.extend(APP_CONFIG, locale);
                            context['address'] = formatMapQuestAddress(locale);

                            var html = JST.did_you_mean_item(context);

                            $did_you_mean.append(html);
                        });

                        $search_help.show();
                        // $search_help_us.hide();
                    }
            });
        }  
    });
});
