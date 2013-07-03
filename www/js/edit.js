var $edit_map = null;
var $search_address = null;
var $search_address_button = null;
var $search_help = null;
var $did_you_mean = null;
var $no_geocode = null;
var $geolocate_button = null;

var $possible_street = null;
var $possible_city = null;
var $possible_state = null;
var $possible_zip_code = null;
var $possible_latitude = null;
var $possible_longitude = null;
var $accept_address = null;

var $address = null;
var $city = null;
var $state = null;
var $zip_code = null;
var $latitude = null;
var $longitude = null;

$(function() {
    $search_address = $('#search-address');
    $search_address_button = $('#search-address-button');
    $search_help = $('#search-help');
    $did_you_mean = $('#did-you-mean-edit');
    $no_geocode = $('#no-geocode');
    $geolocate_button = $('#geolocate');

    $possible_street = $('#possible-street');
    $possible_city = $('#possible-city');
    $possible_state = $('#possible-state');
    $possible_zip_code = $('#possible-zip');
    $possible_latitude = $('#possible-latitude');
    $possible_longitude = $('#possible-longitude');
    $accept_address = $('#accept-address')

    $address = $('input[name="address"]');
    $city = $('input[name="city"]');
    $state = $('input[name="state"]');
    $zip_code = $('input[name="zip_code"]');
    $latitude = $('input[name="latitude"]');
    $longitude = $('input[name="longitude"]');

    /*
    * We only want to submit changed formfields to the server for processing.
    * Script marks each changed field base on blur/change.
    * Could alert with a warning about what fields you've changed before POSTing.
    */
    $('#playground-form .input').blur(function(){
        $(this).attr('data-changed', 'true');
    });

    // Fire on button click. Not on enter.
    $('#playground-update').on('click', function(){

        // Loop over the inputs inside the form.
        $.each($('#playground-form .input'), function(index, item) {

            // I removed this bit and replaced it in the form HTML.
            // This was still submitting every item in the form, which
            // Isn't what we want; only the stuff that's changed
            // should have a 'name' attribute.

            // if ($(item).attr('name')) {
            //     return;
            // }

            // Check to see if this item has changed.
            // If it has not changed, remove its name attribute
            // so that it will not submit with the form.
            if ($(item).attr('data-changed') != 'true') {
                $(item).removeAttr('name');
            }
        });

        // Submit the form.
        $('#playground-form').submit();

        return false;
    });

    map = L.map('edit-map');
    map_layer = L.mapbox.tileLayer(APP_CONFIG.MAPBOX_BASE_LAYER, {
        detectRetina: true,
        retinaVersion: APP_CONFIG.MAPBOX_BASE_LAYER_RETINA
    }).addTo(map);
    grid_layer = L.mapbox.gridLayer('geraldrich.map-h0glukvl').addTo(map);
    map.addControl(L.mapbox.gridControl(grid_layer));

    $('#edit-playground').on('shown', function() {
        var left = $('#edit-map').width()/2 - 8;
        var top = $('#edit-map').height()/2 - 8;
        $('#edit-marker').css({'left': left, 'top': top});
    });

    if ($latitude.val() !== '' && $longitude.val() !== '') {
        map.setView([$latitude.val(), $longitude.val()], 12);

        var address_bits = [];
        if ($address.val()) {
            address_bits.push($address.val());
        }
        if ($city.val()) {
            address_bits.push($city.val() + ',');
        }
        if ($state.val()) {
            address_bits.push($state.val());
        }
        if ($zip_code.val()) {
            address_bits.push($zip_code.val());
        }

        $search_address.val(address_bits.join(' '));
    } else {
        map.setView([38.9, -77], 12);
    }

    $search_address_button.click(function() {
        var address = $search_address.val();

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

                        map.setView([locale['latLng']['lat'], locale['latLng']['lng']], 12);
                        $possible_street.val(locale['street']);
                        $possible_city.val(locale['adminArea5']);
                        $possible_state.val(locale['adminArea3']);
                        $possible_zip_code.val(locale['postalCode']);
                        $possible_latitude.val(locale['latLng']['lat']);
                        $possible_longitude.val(locale['latLng']['lng']);

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
                    }
                }
            });
        }  
    });

    $did_you_mean.on('click', 'li', function() {
        var $this = $(this);
        var street = $this.data('street');
        var city = $this.data('city');
        var state = $this.data('state');
        var zip = $this.data('zip');
        var latitude = $this.data('latitude');
        var longitude = $this.data('longitude');

        map.setView([latitude, longitude], 12);

        $possible_street.val(street);
        $possible_city.val(city);
        $possible_state.val(state);
        $possible_zip_code.val(zip);
        $possible_latitude.val(latitude);
        $possible_longitude.val(longitude);

        $search_help.hide();
    });

    var reverseGeocodeCallback = function(locale) {
        $possible_street.val(locale['street']);
        $possible_city.val(locale['adminArea5']);
        $possible_state.val(locale['adminArea3']);
        $possible_zip_code.val(locale['postalCode']);
        $possible_latitude.val(locale['latLng']['lat']);
        $possible_longitude.val(locale['latLng']['lng']);

        $search_address.val(formatMapQuestAddress(locale));
    }

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(function(position) {
            $search_help.hide();
            $no_geocode.hide();

            map.setView([position.coords.latitude, position.coords.longitude], 12);

            reverseGeocode(position.coords.latitude, position.coords.longitude, reverseGeocodeCallback)
        });
    });

    $accept_address.click(function() {
        if ($address.val() != $possible_street.val()) {
            $address.attr('data-changed', 'true');
            $address.val($possible_street.val())
        }

        if ($city.val() != $possible_city.val()) {
            $city.attr('data-changed', 'true');
            $city.val($possible_city.val());
        }

        var state = STATE_NAME_TO_CODE[$possible_state.val()];

        if ($state.val() != state) {
            $state.attr('data-changed', 'true');
            $state.val(state);
        }

        if ($zip_code.val() != $possible_zip_code.val()) {
            $zip_code.attr('data-changed', 'true');
            $zip_code.val($possible_zip_code.val());
        }

        if ($latitude.val() != $possible_latitude.val()) {
            $latitude.attr('data-changed', 'true');
            $latitude.val($possible_latitude.val());
        }

        if ($longitude.val() != $possible_longitude.val()) {   
            $longitude.attr('data-changed', 'true');
            $longitude.val($possible_longitude.val());
        }
    });

    map.on('moveend', function() {
        var latlng = map.getCenter();
        reverseGeocode(latlng.lat,latlng.lng, reverseGeocodeCallback);
    })
});
