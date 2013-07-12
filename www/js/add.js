var $edit_map = null;
var $locator_map = null;
var $no_geocode = null;
var $geolocate_button = null;
var $modal_map = null;

var $address = null;
var $city = null;
var $geo_state = null;
var $zip_code = null;
var $latitude = null;
var $longitude = null;
var $playground_meta_hdr = null;
var $playground_meta_items = null;
var $reverse_geocoded = null;
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
    $reverse_geocoded = $('input[name="reverse_geocoded"]');

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
        if ( REVERSE_GEOCODE === false ) {

            var address_string = '';
            address_string += $address.val() + ' ';
            address_string += $city.val() + ', ';
            address_string += $geo_state.val() + ' ';
            address_string += $zip_code.val();

            geocode(address_string, geocodeCallback);

        } else {

            prepAddress();
            $reverse_geocoded.attr('checked', 'checked');
            $reverse_geocoded.attr('data-changed', 'true');

            submitForm();
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

        unitedStatesCheck(locale);
        prepAddress();
        submitForm();
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
            // $search_help.hide();
            // $no_geocode.hide();

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

    var submitForm = function() {
        if ( $('input[name="name"]').val() === '' || $address.val() === '' ){
            alert('You are missing form fields.');
        } else {
            $('#playground-form').submit();
        }
    };

    var prepAddress = function() {
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
    };

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
