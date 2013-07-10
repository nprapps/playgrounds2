var $edit_map = null;
var $locator_map = null;
var $no_geocode = null;
var $geolocate_button = null;
var $modal_map = null;

var $address = null
var $edit_map = null;
var $locator_map = null;
var $modal_map = null;
var $toggle_address_button = null;
var $address_editor = null;
var $address_placeholder = null;
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
var $playground_meta_hdr = null;
var $playground_meta_items = null;

var $edit_alert = null;

var BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER;
var CONTENT_WIDTH;
var GEOLOCATE = Modernizr.geolocation;
var LOCATOR_DEFAULT_ZOOM = 15;
var PAGE_WIDTH;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 8;
var RESULTS_DEFAULT_ZOOM = 14;
var RETINA = window.devicePixelRatio > 1;
if (RETINA) {
    BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER_RETINA;
    LOCATOR_DEFAULT_ZOOM += 1;
    RESULTS_DEFAULT_ZOOM += 1;
}

var REVERSE_GEOCODE = false;

var is_playground = false;

function get_parameter_by_name(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function center_editor_map(){
    map.invalidateSize(false);
    var marker_left = $('#edit-map').width()/2 - 8;
    var marker_top = $('#edit-map').height()/2 - 8;
    $('#edit-marker').css({'left': marker_left, 'top': marker_top});
}

function resize_locator_map() {
    CONTENT_WIDTH = $('#main-content').width();
    PAGE_WIDTH = $('body').outerWidth();
    var lat = $locator_map.data('latitude');
    var lon = $locator_map.data('longitude'); // Because iOS refuses to obey toString()
    var map_path;
    var new_height;
    var new_width = CONTENT_WIDTH;

    if (PAGE_WIDTH > 480) {
        new_width = Math.floor(new_width / 2) - 22;
    }
    new_height = Math.floor(CONTENT_WIDTH / 3);

    if (RETINA) {
        new_width = new_width * 2;
        if (new_width > 640) {
            new_width = 640;
        }
        new_height = Math.floor(new_width / 3);
    }

    map_path = 'http://api.tiles.mapbox.com/v3/' + BASE_LAYER + '/pin-m-star+ff6633(' + lon + ',' + lat + ')/' + lon + ',' + lat + ',' + LOCATOR_DEFAULT_ZOOM + '/' + new_width + 'x' + new_height + '.png';
    $locator_map.attr('src', map_path);
    $modal_map.attr('src', map_path);
}

function toggle_address_button(){
    $('#address-editor').toggleClass('hide');
    $toggle_address_button.toggleClass('btn-success');
    var button_text = $toggle_address_button.text() === 'Edit' ? 'Cancel' : 'Edit';
    $toggle_address_button.text(button_text);
    center_editor_map();
}

function search_address(){
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

                if (locales.length === 0) {
                    $did_you_mean.append('<li>No results</li>');

                    $no_geocode.show();
                } else if (locales.length == 1) {
                    var locale = locales[0];

                    map.setView([locale['latLng']['lat'], locale['latLng']['lng']], LOCATOR_DEFAULT_ZOOM);
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
}

$(function() {
    $locator_map = $('#locator-map');
    $modal_map = $('#modal-locator-map');
    $toggle_address_button = $('#toggle-address-button');
    $address_editor = $('#address-editor');
    $address_placeholder = $('#address-placeholder');
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
    $accept_address = $('#accept-address');

    $address = $('input[name="address"]');
    $city = $('input[name="city"]');
    $state = $('input[name="state"]');
    $zip_code = $('input[name="zip_code"]');
    $latitude = $('input[name="latitude"]');
    $longitude = $('input[name="longitude"]');
    $playground_meta_hdr = $('#main-content').find('.about').find('h5.meta');
    $playground_meta_items = $('#main-content').find('.about').find('ul.meta');
    $reverse = $('input[name="reverse_geocoded"]');
    $edit_alert = $('#edit-alert');

    $geocode_button = $('#path-geocode');
    $reverse_geocode_button = $('#path-reverse-geocode');

    is_playground = $('body').hasClass('playground');

    // Show the success alert if document location has the correct query string flag
    if (get_parameter_by_name('action') === 'editing_thanks'){
        $edit_alert.toggleClass('hide');
    }

    // Toggle the address edit interface
    $('#toggle-address-button, #modal-locator-map').on('click', function(){
        toggle_address_button();
    });


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

    map = L.map('edit-map', {
        minZoom: 11,
        scrollWheelZoom: false
    });

    map_layer = L.mapbox.tileLayer(BASE_LAYER).addTo(map);
    grid_layer = L.mapbox.gridLayer(BASE_LAYER).addTo(map);
    map.addControl(L.mapbox.gridControl(grid_layer));
    center_editor_map();

    $('#address-editor').on('shown', function() {
        center_editor_map();
    });

    if ($latitude.val() !== '' && $longitude.val() !== '') {
        map.setView([$latitude.val(), $longitude.val()], LOCATOR_DEFAULT_ZOOM);

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

    var geocodeCallback = function(locale) {
        $latitude.val(locale['latLng']['lat']);
        $longitude.val(locale['latLng']['lng']);
    };

    var reverseGeocodeCallback = function(locale) {
        $possible_street.val(locale['street']);
        $possible_city.val(locale['adminArea5']);
        $possible_state.val(locale['adminArea3']);
        $possible_zip_code.val(locale['postalCode']);
        $possible_latitude.val(locale['latLng']['lat']);
        $possible_longitude.val(locale['latLng']['lng']);

        $search_address.val(formatMapQuestAddress(locale));
    };

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(function(position) {
            $search_help.hide();
            $no_geocode.hide();

            map.setView([position.coords.latitude, position.coords.longitude], LOCATOR_DEFAULT_ZOOM);

            reverseGeocode(position.coords.latitude, position.coords.longitude, reverseGeocodeCallback);
        });
    });

    $accept_address.click(function() {
        if ( REVERSE_GEOCODE === false ) {
            var address_string = '';
            address_string += $possible_street.val() + ' ';
            address_string += $possible_city.val() + ', ';
            address_string += $possible_state.val() + ' ';
            address_string += $possible_zip_code.val();

            console.log(address_string);

            geocode(address_string, geocodeCallback);
        }

        var placeholder_text = '';

        if ($address.val() != $possible_street.val()) {
            $address.attr('data-changed', 'true');
            $address.val($possible_street.val());
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
            $locator_map.data('latitude', $latitude.val());
        }

        if ($longitude.val() != $possible_longitude.val()) {
            $longitude.attr('data-changed', 'true');
            $longitude.val($possible_longitude.val());
            $locator_map.data('longitude', $longitude.val());
        }

        placeholder_text = $address.val() + '<br>' + $city.val() + ', ' + $state.val();

        resize_locator_map();
        $('#address-placeholder p').html(placeholder_text);
        toggle_address_button();
    });

    map.on('moveend', function() {
        var latlng = map.getCenter();
        reverseGeocode(latlng.lat,latlng.lng, reverseGeocodeCallback);
    });

    CONTENT_WIDTH = $('#main-content').width();
    PAGE_WIDTH = $('body').outerWidth();
    RESULTS_MAP_WIDTH = CONTENT_WIDTH;
    RESULTS_MAP_HEIGHT = CONTENT_WIDTH;

    if (is_playground) {
        if ($('#locator-map')) {
            resize_locator_map();
            $(window).resize(_.debounce(resize_locator_map,100));
        }

        $('.playground-features i').tooltip( { trigger: 'click' } );

        $playground_meta_hdr.html($playground_meta_hdr.html() + ' &rsaquo;');
        $playground_meta_items.hide();

        $playground_meta_hdr.on('click', function() {
            $playground_meta_items.slideToggle('fast');
        });
    }

    $geocode_button.on('click', function(){
        REVERSE_GEOCODE = false;
        $('.address-form').addClass('hidden');
        $('.path-geocode').removeClass('hidden');
        $('#accept-address').removeClass('hidden');
    });

    $reverse_geocode_button.on('click', function(){
        REVERSE_GEOCODE = true;
        $('.address-form').addClass('hidden');
        $('.path-reverse-geocode').removeClass('hidden');
        $('#accept-address').removeClass('hidden');
        center_editor_map();
    });

});;
var $city = null;
var $geo_state = null;
var $zip_code = null;
var $latitude = null;
var $longitude = null;
var $playground_meta_hdr = null;
var $playground_meta_items = null;

var $edit_alert = null;

var BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER;
var CONTENT_WIDTH;
var GEOLOCATE = Modernizr.geolocation;
var LOCATOR_DEFAULT_ZOOM = 15;
var PAGE_WIDTH;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 8;
var RESULTS_DEFAULT_ZOOM = 14;
var RETINA = window.devicePixelRatio > 1;
if (RETINA) {
    BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER_RETINA;
    LOCATOR_DEFAULT_ZOOM += 1;
    RESULTS_DEFAULT_ZOOM += 1;
}

var REVERSE_GEOCODE = false;

var is_playground = false;

function get_parameter_by_name(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function center_editor_map(){
    map.invalidateSize(false);
    var marker_left = $('#edit-map').width()/2 - 8;
    var marker_top = $('#edit-map').height()/2 - 8;
    $('#edit-marker').css({'left': marker_left, 'top': marker_top});
}

function resize_locator_map() {
    CONTENT_WIDTH = $('#main-content').width();
    PAGE_WIDTH = $('body').outerWidth();
    var lat = $locator_map.data('latitude');
    var lon = $locator_map.data('longitude'); // Because iOS refuses to obey toString()
    var map_path;
    var new_height;
    var new_width = CONTENT_WIDTH;

    if (PAGE_WIDTH > 480) {
        new_width = Math.floor(new_width / 2) - 22;
    }
    new_height = Math.floor(CONTENT_WIDTH / 3);

    if (RETINA) {
        new_width = new_width * 2;
        if (new_width > 640) {
            new_width = 640;
        }
        new_height = Math.floor(new_width / 3);
    }

    map_path = 'http://api.tiles.mapbox.com/v3/' + BASE_LAYER + '/pin-m-star+ff6633(' + lon + ',' + lat + ')/' + lon + ',' + lat + ',' + LOCATOR_DEFAULT_ZOOM + '/' + new_width + 'x' + new_height + '.png';
    $locator_map.attr('src', map_path);
    $modal_map.attr('src', map_path);
}

$(function() {
    $locator_map = $('#locator-map');
    $modal_map = $('#modal-locator-map');
    $no_geocode = $('#no-geocode');
    $geolocate_button = $('#geolocate');

    $address = $('input[name="address"]');
    $city = $('input[name="city"]');
    $geo_state = $('input[name="state"]');
    $zip_code = $('input[name="zip_code"]');
    $latitude = $('input[name="latitude"]');
    $longitude = $('input[name="longitude"]');

    $playground_meta_hdr = $('#main-content').find('.about').find('h5.meta');
    $playground_meta_items = $('#main-content').find('.about').find('ul.meta');
    $reverse = $('input[name="reverse_geocoded"]');
    $edit_alert = $('#edit-alert');

    $geocode_button = $('#path-geocode');
    $reverse_geocode_button = $('#path-reverse-geocode');

    is_playground = $('body').hasClass('playground');

    // Show the success alert if document location has the correct query string flag
    if (get_parameter_by_name('action') === 'editing_thanks'){
        $edit_alert.toggleClass('hide');
    }

    /*
    * We only want to submit changed formfields to the server for processing.
    * Script marks each changed field base on blur/change.
    * Could alert with a warning about what fields you've changed before POSTing.
    */
    $('#playground-form .input').blur(function(){
        $(this).attr('data-changed', 'true');
    });

    $('#playground-update').on('click', function(){
        // Loop over the inputs inside the form.
        $.each($('#playground-form .input'), function(index, item) {
            if ($(item).attr('data-changed') != 'true') {
                $(item).removeAttr('name');
            }
        });

        if ( REVERSE_GEOCODE === false ) {
            var address_string = '';
            address_string += $address.val() + ' ';
            address_string += $city.val() + ', ';
            address_string += $geo_state.val() + ' ';
            address_string += $zip_code.val();

            geocode(address_string, geocodeCallback);
        } else {
            prepAddress();
            $('#playground-form').submit();
        }
        return false;
    });

    map = L.map('edit-map', {
        minZoom: 11,
        scrollWheelZoom: false
    });

    map_layer = L.mapbox.tileLayer(BASE_LAYER).addTo(map);
    grid_layer = L.mapbox.gridLayer(BASE_LAYER).addTo(map);
    map.addControl(L.mapbox.gridControl(grid_layer));
    center_editor_map();

    if ($latitude.val() !== '' && $longitude.val() !== '') {
        map.setView([$latitude.val(), $longitude.val()], LOCATOR_DEFAULT_ZOOM);
    } else {
        map.setView([38.9, -77], 12);
    }

    var geocodeCallback = function(locale) {
        $latitude.attr('value', locale['latLng']['lat']);
        $longitude.attr('value', locale['latLng']['lng']);

        prepAddress();
        $('#playground-form').submit();
    };

    var reverseGeocodeCallback = function(locale) {
        $address.val(locale['street']);
        $city.val(locale['adminArea5']);
        $geo_state.val(locale['adminArea3']);
        $zip_code.val(locale['postalCode']);
        $latitude.val(locale['latLng']['lat']);
        $longitude.val(locale['latLng']['lng']);
    };

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(function(position) {
            $search_help.hide();
            $no_geocode.hide();

            map.setView([position.coords.latitude, position.coords.longitude], LOCATOR_DEFAULT_ZOOM);

            reverseGeocode(position.coords.latitude, position.coords.longitude, reverseGeocodeCallback);
        });
    });

    map.on('moveend', function() {
        var latlng = map.getCenter();
        reverseGeocode(latlng.lat,latlng.lng, reverseGeocodeCallback);
    });

    CONTENT_WIDTH = $('#main-content').width();
    PAGE_WIDTH = $('body').outerWidth();
    RESULTS_MAP_WIDTH = CONTENT_WIDTH;
    RESULTS_MAP_HEIGHT = CONTENT_WIDTH;

    if (is_playground) {
        if ($('#locator-map')) {
            resize_locator_map();
            $(window).resize(_.debounce(resize_locator_map,100));
        }

        $('.playground-features i').tooltip( { trigger: 'click' } );

        $playground_meta_hdr.html($playground_meta_hdr.html() + ' &rsaquo;');
        $playground_meta_items.hide();

        $playground_meta_hdr.on('click', function() {
            $playground_meta_items.slideToggle('fast');
        });
    }

    function prepAddress() {
        $address.attr('data-changed', 'true');
        $city.attr('data-changed', 'true');
        $geo_state.attr('data-changed', 'true');
        $zip_code.attr('data-changed', 'true');

        if (REVERSE_GEOCODE === true) {
            var state = STATE_NAME_TO_CODE[$geo_state.val()];
            $geo_state.val(state);
        }

        $latitude.attr('data-changed', 'true');
        $locator_map.data('latitude', $latitude.val());

        $longitude.attr('data-changed', 'true');
        $locator_map.data('longitude', $longitude.val());
        resize_locator_map();
    }

    $geocode_button.on('click', function(){
        REVERSE_GEOCODE = false;
        $('.address-form').addClass('hidden');
        $('.path-geocode').removeClass('hidden');
        $('#accept-address').removeClass('hidden');
        $city.parent('div').parent('div').toggle();
        $geo_state.parent('div').parent('div').toggle();
        $zip_code.parent('div').parent('div').toggle();
        $address.parent('div').parent('div').toggle();
    });

    $reverse_geocode_button.on('click', function(){
        REVERSE_GEOCODE = true;
        $('.address-form').addClass('hidden');
        $('.path-reverse-geocode').removeClass('hidden');
        $('#accept-address').removeClass('hidden');
        center_editor_map();
        $city.parent('div').parent('div').toggle();
        $geo_state.parent('div').parent('div').toggle();
        $zip_code.parent('div').parent('div').toggle();
        $address.parent('div').parent('div').toggle();
    });

});
