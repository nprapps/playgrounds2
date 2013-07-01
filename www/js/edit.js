var $edit_map = null;
var $address = null;
var $search_address = null;
var $search_help = null;
var $did_you_mean = null;
var $no_geocode = null;

$(function() {
    $address = $('#address');
    $search_address = $('#search-address');
    $search_help = $('#search-help');
    $did_you_mean = $('#did-you-mean-edit');
    $no_geocode = $('#no-geocode');

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
            $search_help.hide();
            $no_geocode.hide();

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

                        $no_geocode.show();
                    } else if (locales.length == 1) {
                        var locale = locales[0];

                        // $search_latitude.val(locale['latLng']['lat']);
                        // $search_longitude.val(locale['latLng']['lng']);
                        console.log('Found it');

                        // $results_address.html('Showing results near ' + formatMapQuestAddress(locale));
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
                }
            });
        }  
    });

    $did_you_mean.on('click', 'li', function() {
        var $this = $(this);
        var address = $this.data('address');
        var latitude = $this.data('latitude');
        var longitude = $this.data('longitude');

        console.log(latitude);

        // $search_latitude.val(latitude);
        // $search_longitude.val(longitude);
        // $results_address.html('Showing results near ' + address);

        $search_help.hide();
        // $search_help_us.show();

    });

});
