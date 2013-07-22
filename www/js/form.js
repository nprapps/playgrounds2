$(function() {
    var playground = {
        'ACTION': get_parameter_by_name('action'),
        'BASE_LAYER': APP_CONFIG.MAPBOX_BASE_LAYER,
        'CONTENT_WIDTH': 0,
        'GEOLOCATE': Modernizr.geolocation,
        'LOCATOR_DEFAULT_ZOOM': 15,
        'PAGE_WIDTH': 0,
        'RESULTS_MAP_WIDTH': 500,
        'RESULTS_MAP_HEIGHT': 500,
        'RESULTS_MAX_ZOOM': 16,
        'RESULTS_MIN_ZOOM': 8,
        'RESULTS_DEFAULT_ZOOM': 14,
        'RETINA': window.devicePixelRatio > 1,
        'fields': {
            // Many other fields are set dynamically.
            'locator_map': $('#locator-map'),
            'modal_map': $('#modal-locator-map'),
            'meta_items': $('#main-content').find('.about').find('ul.meta'),
            'meta_hdr': $('#main-content').find('.about').find('h5.meta')
        },
        'callbacks': {
            'geocode': function(locale) {
                if (locale){
                    playground.fields.latitude.attr('value', locale['latLng']['lat']);
                    playground.fields.longitude.attr('value', locale['latLng']['lng']);
                    require_us_address(locale);
                    playground.form.geocode_fields();
                    playground.toggle_address_button();
                } else {
                    make_alert('We can\'t find a place with that name.\nWant to try again?', 'warning');
                }
            },
            'reverse_geocode': function(locale) {
                playground.fields.address.val(locale['street']);
                playground.fields.city.val(locale['adminArea5']);

                // States are special. Handle them specially.
                if (locale['adminArea3'] == 'District of Columbia') { 
                    var short_state = STATE_NAME_TO_CODE[locale['adminArea3']];
                    playground.fields.state.val(short_state);
                    $('select[name="state"] option[value="'+ short_state +'""]').attr('selected', 'selected');
                } else {
                    playground.fields.state.val(locale['adminArea3']);
                    $('select[name="state"] option[value="'+ locale['adminArea3'] +'""]').attr('selected', 'selected');
                }

                // playground.fields.state.attr('selected', 'selected');
                playground.fields.zip_code.val(locale['postalCode']);
                playground.fields.latitude.val(locale['latLng']['lat']);
                playground.fields.longitude.val(locale['latLng']['lng']);

                require_us_address(locale);
                playground.form.geocode_fields();
            }
        },
        'form': {
            'validate': function() {
                var required_fields = $("#form input[data-required='true']");
                var flagged_fields = [];
                $.each(required_fields, function(index, required_field){
                    if (required_field.val === '') {
                        flagged_fields.push(required_field);
                    }
                });
                if (flagged_fields.length > 0){
                    playground.form.flag_fields(flagged_fields);
                    return false;
                } else {
                    return true;
                }
            },
            'flag_fields': function(flagged_fields) {
                $(required_field).addClass('flagged');
            },
            'prepare_geocode_object': function() {
                geocode_string = '{location:{';
                geocode_string += 'street:"' + playground.fields.address.val() +'",';
                if (playground.fields.city.val() !== '' && playground.fields.state.val() !== 'DC') {
                    geocode_string += 'adminArea5:"' + playground.fields.city.val() +'",';
                }
                if (playground.fields.state.val() !== '' && playground.fields.state.val() !== 'DC') {
                    geocode_string += 'adminArea3:"' + STATE_CODE_TO_NAME[playground.fields.state.val()] +'",';
                }
                if (playground.fields.state.val() == 'DC') {
                    geocode_string += 'adminArea4:"District of Columbia",';
                }
                if (playground.fields.zip_code.val() !== '') {
                    geocode_string += 'postalCode:"' + playground.fields.zip_code.val() +'",';
                }
                return geocode_string + '}}';
            },
            'geocode_fields': function() {
                // Set the base location fields to 'changed' so that they will POST.
                playground.fields.address.attr('data-changed', 'true');
                playground.fields.city.attr('data-changed', 'true');
                playground.fields.state.attr('data-changed', 'true');
                playground.fields.zip_code.attr('data-changed', 'true');
                playground.fields.latitude.attr('data-changed', 'true');
                playground.fields.longitude.attr('data-changed', 'true');

                // Reset the locator map.
                playground.fields.locator_map.data('latitude', playground.fields.latitude.val());
                playground.fields.locator_map.data('longitude', playground.fields.longitude.val());

                // Set the map state.
                playground.map.resize_locator();
            }
        },
        'map': {
            'setup': function() {
                /*
                * Initializes the map.
                */
                map = L.map('edit-map', {
                    minZoom: 11,
                    maxZoom: 17,
                    scrollWheelZoom: false
                });

                map_layer = L.mapbox.tileLayer(playground.BASE_LAYER).addTo(map);
                grid_layer = L.mapbox.gridLayer(playground.BASE_LAYER).addTo(map);
                map.addControl(L.mapbox.gridControl(grid_layer));

                if (playground.fields.latitude.val() !== '' && playground.fields.longitude.val() !== '') {
                    map.setView([
                            playground.fields.latitude.val(),
                            playground.fields.longitude.val()],
                        playground.LOCATOR_DEFAULT_ZOOM);
                } else {
                    map.setView([38.9, -77], 12);
                }
                playground.map.center_editor();
            },
            'center_editor': function() {
                map.invalidateSize(false);
                var marker_left = $('#edit-map').width()/2 - 8;
                var marker_top = $('#edit-map').height()/2 - 8;
                $('#edit-marker').css({'left': marker_left, 'top': marker_top});
            },
            'resize_locator': function() {
                // Set the width.
                playground.CONTENT_WIDTH = $('#main-content').width();
                playground.PAGE_WIDTH = $('body').outerWidth();

                // Set the map coords.
                var lat = playground.fields.latitude.val();
                var lon = playground.fields.longitude.val();
                var map_path;
                var new_height;
                var new_width = playground.CONTENT_WIDTH;

                if (playground.PAGE_WIDTH > 480) {
                    new_width = Math.floor(new_width / 2) - 22;
                }
                new_height = Math.floor(playground.CONTENT_WIDTH / 3);

                if (playground.RETINA) {
                    new_width = new_width * 2;
                    if (new_width > 640) {
                        new_width = 640;
                    }
                    new_height = Math.floor(new_width / 3);
                }

                // Set up the map image.
                map_path = 'http://api.tiles.mapbox.com/v3/';
                map_path += playground.BASE_LAYER + '/pin-m-star+ff6633(' + lon + ',' + lat + ')/';
                map_path += lon + ',' + lat + ',' + playground.LOCATOR_DEFAULT_ZOOM + '/';
                map_path += new_width + 'x' + new_height + '.png';

                playground.fields.locator_map.attr('src', map_path);
                playground.fields.modal_map.attr('src', map_path);

                // Set the placeholder text.
                placeholder_text = playground.fields.address.val();
                placeholder_text += '<br>' + playground.fields.city.val();
                placeholder_text += ', ' + playground.fields.state.val();
                $('#address-placeholder p').html(placeholder_text);
            }
        },
        'locate_me': function() {
            function success(position){
                map.setView([position.coords.latitude, position.coords.longitude], playground.LOCATOR_DEFAULT_ZOOM);
                playground.reverse_geocode(position.coords.latitude, position.coords.longitude, playground.callbacks.reverse_geocode);
                $('#modal-locator-map').removeClass('hidden');
            }

            function error(){
                $('#myTab a:last').tab('show');
            }

            navigator.geolocation.getCurrentPosition(success, error);
        },
        'geocode': function(geocode_object, callback) {
            $.ajax({
                'url': 'http://open.mapquestapi.com/geocoding/v1/?inFormat=json&json='+ geocode_object,
                'dataType': 'jsonp',
                'contentType': 'application/json',
                'success': function(data) {
                    var locales = data['results'][0]['locations'];
                    var locale;
                    if (locales.length !== 0) {
                        locale = locales[0];
                    }
                    var zip_list = [];
                    callback(locale);
                }
            });
        },
        'reverse_geocode': function(latitude, longitude, callback) {
            $.ajax({
                'url': 'http://open.mapquestapi.com/geocoding/v1/reverse',
                'data': { 'location': latitude + ',' + longitude },
                'dataType': 'jsonp',
                'contentType': 'application/json',
                'success': function(data) {
                    var locales = data['results'][0]['locations'];
                    var locale = locales[0];
                    var zip_list = [];

                    if (locale['adminArea4'] == 'District of Columbia')  {
                        locale['adminArea5'] = 'Washington';
                        locale['adminArea3'] = 'District of Columbia';
                    }

                    callback(locale);
                }
            });
        },
        'accept_address': function() {
            playground.geocode(playground.form.prepare_geocode_object(), playground.callbacks.geocode);
        },
        'toggle_address_button': function(){
            $('.address-editor').toggleClass('hide');
            playground.map.center_editor();
            $('#toggle-address-button').toggleClass('btn-success').text($('#toggle-address-button').text() === 'Edit' ? 'Cancel' : 'Edit');
        },
        'submit': function() {
            if ( playground.fields.reverse_geocode.attr('checked') !== 'checked' ) {
                playground.geocode(playground.form.prepare_geocode_object(), playground.callbacks.geocode);
            } else {
                playground.form.geocode_fields();
                playground.fields.reverse_geocoded.attr('checked', 'checked');
                playground.fields.reverse_geocoded.attr('data-changed', 'true');
                $('#form').submit();
            }
            return false;
        },
        'setup': function() {
            // Set all of the playground field names.
            // List of fields we'd like to set up.
            var field_list = [
                'address',
                'city',
                'zip_code',
                'latitude',
                'longitude',
                'reverse_geocoded'
            ];

            // Loop and add a playgrounds.field attribute for each of these fields.
            $.each(field_list, function(index, field_name){
                playground.fields[field_name] = $('input[name="' + field_name + '"]');
            });

            // Except for states because they're selectable.
            playground.fields.state = $('select[name="state"]');
            playground.fields.state_selected = $('select[name="state"] option:selected');

            // Watch the state selector.
            // Update the state_selected and state value.
            playground.fields.state.on('change', function(){
                playground.fields.state_selected = $('select[name="state"] option:selected');
                playground.fields.state.val(playground.fields.state_selected.val());
            });

            // Set up the screen width constants.
            playground.CONTENT_WIDTH = $('#main-content').width();
            playground.PAGE_WIDTH = $('body').outerWidth();
            playground.RESULTS_MAP_WIDTH = playground.CONTENT_WIDTH;
            playground.RESULTS_MAP_HEIGHT = playground.CONTENT_WIDTH;
            if (playground.RETINA) {
                playground.BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER_RETINA;
                playground.LOCATOR_DEFAULT_ZOOM += 1;
                playground.RESULTS_DEFAULT_ZOOM += 1;
            }

            // Set up the map.
            playground.map.setup();

            // Watch the map.
            // Perform a reverse geocode when the map is finished moving.
            map.on('moveend', function() {
                var latlng = map.getCenter();
                playground.reverse_geocode(latlng.lat, latlng.lng, playground.callbacks.reverse_geocode);
            });

            // Sets up the click functions for each of the buttons.
            // Requires a data-action attribute on the button element.
            $('#form .btn').each(function(index, action){
                $(this).on('click', function(){
                    playground[$(this).attr('data-action')]($(this).attr('data-path'));
                    return false;
                });
            });

            // Watch for changes to the playground form.
            $('#form .input').blur(function(){

                // Set a changed attribute.
                $(this).attr('data-changed', 'true');

                // Remove a validation flag, if it exists.
                $(this).removeClass('flagged');
            });

            // Check to see if we've got a message to show.
            if (playground.ACTION !== null){

                // We'll name the message div after the URL param.
                $('#' + playground.ACTION).toggleClass('hide');
            }

            // Set up the features tooltip.
            $('.playground-features i').tooltip( { trigger: 'click' } );

            // Do this thing with the map.
            if ( $('#locator-map') ) {
                playground.map.resize_locator();
                $(window).resize(_.debounce(playground.map.resize_locator_map, 100));
            }

            // All of this meta_hdr and meta_items stuff.
            playground.fields.meta_hdr.html(playground.fields.meta_hdr.html() + ' &rsaquo;');
            playground.fields.meta_items.hide();
            playground.fields.meta_hdr.on('click', function() {
                playground.fields.meta_items.slideToggle('fast');
            });

            // Lock down the double-modal.
            $('.modal').on('shown', function(){
                $('body').on('touchmove', prevent_body_scroll(event));
            });
            $('.modal').on('hidden', function(){
                $('body').off('touchmove', prevent_body_scroll(event));
            });
            $('#address-pane').on('shown', function(){
                $('body, #map-pane').on('touchmove', prevent_body_scroll(event));
            });
            $('#address-pane').on('hidden', function(){
                $('body, #map-pane').off('touchmove', prevent_body_scroll(event));
            });

            if(playground.fields.latitude.val() === '' || playground.fields.longitude.val() === ''){
                playground.locate_me();
            }
        }
    };
    // Initialize the playground object.
    playground.setup();
});
