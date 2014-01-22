var geocoder;
var street_number;
var street_name;
var city_name;
var state_abbreviation;
var zip_code;
var playground = {};

$(function() {
    playground = {
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
            'address_editor': $('.address-editor'),
            'address_editor_toggle': $('#toggle-address-button'),
            'meta_hdr': $('#main-content').find('.playground-features').find('h5.meta'),
            'meta_items': $('#main-content').find('.playground-features').find('ul.meta'),
            'meta_comments': $('#main-content').find('.comments').find('p.meta'),
            'meta_guidelines': $('#main-content').find('.comments').find('p.guidelines'),
            'meta_changelog': $('#main-content').find('.changelog').find('h5.meta'),
            'meta_changes': $('#main-content').find('.changelog').find('ul.meta')
        },
        'inputs': {
            'text_input': $('#form input[type="text"], #form select'),
            'checkbox': $('#form input[type="checkbox"]')
        },
        'initial_field_values': {},
        'callbacks': {
            'geocode': function(address_components, latlng) {
                if (address_components){
                    playground.fields.latitude.attr('value', latlng['location']['d']);
                    playground.fields.longitude.attr('value', latlng['location']['e']);
                    require_us_address(address_components);
                    playground.form.geocode_fields();
                    playground.hide_address_editor();
                    map.off('moveend', playground.map.process_map_location);
                    playground.map.reset_editor();
                    map.on('moveend', playground.map.process_map_location);
                    playground.address_change_accepted = true;
                } else {
                    alert_text = "<strong>We're sorry! We couldn't find that place.</strong><br>Don't forget to add the street/avenue/boulevard.<br/>If you're still having trouble, try finding it on the map.";
                    make_alert(alert_text, 'alert-error', 'div.modal-alerts')
                }
            },
            'reverse_geocode': function(address_components, latlng) {
                console.log(address_components);
                address_components.forEach(function(address) {
                    if (address['types'][0] == 'street_number') {
                        street_number = address['long_name'];
                    }
                    if (address['types'][0] == 'route' || address['types'][0] == 'bus_station') {
                        street_name = address['long_name'];
                    }
                    if (address['types'][0] == 'administrative_area_level_3' || address['types'][0] == 'locality') {
                        city_name = address['long_name'];
                    }
                    if (address['types'][0] == 'administrative_area_level_1') {
                        state_abbreviation = address['short_name'];
                    }
                    if (address['types'][0] == 'postal_code') {
                        zip_code = address['long_name'];
                    }
                });

                // sometimes there aren't street numbers
                if (street_number) {
                    playground.fields.address.val(street_number + ' ' + street_name);
                }
                playground.fields.city.val(city_name);

                // States are special. Handle them specially.
                playground.fields.state.val(state_abbreviation);
                $('select[name="state"] option[value="'+ state_abbreviation +'""]').attr('selected', 'selected');

                // playground.fields.state.attr('selected', 'selected');
                playground.fields.zip_code.val(zip_code);
                playground.fields.latitude.val(latlng['d']);
                playground.fields.longitude.val(latlng['e']);

                require_us_address(address_components);
                playground.form.geocode_fields();
                playground.fields.reverse_geocoded.attr('checked', 'checked');

                playground.fields.locator_map.removeClass('hidden');
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
                geocode_string = playground.fields.address.val() + ' ';
                if (playground.fields.city.val() !== '') {
                    geocode_string += playground.fields.city.val() +', ';
                }
                if (playground.fields.state.val() !== '') {
                    geocode_string += STATE_CODE_TO_NAME[playground.fields.state.val()] + ' ';
                }
                if (playground.fields.zip_code.val() !== '') {
                    geocode_string +=  playground.fields.zip_code.val();
                }
                return geocode_string;
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
            },
            'twist_out': function(hed, subhed) {
                hed.html(hed.html() + ' +');
                subhed.hide();
                hed.on('click', function() {
                    subhed.slideToggle('fast');
                });
            }
        },
        'map': {
            'setup': function() {
                /*
                * Initializes the map.
                */

                $('#edit-marker').hide();

                map = L.map('edit-map', {
                    minZoom: 11,
                    maxZoom: 17,
                    scrollWheelZoom: false
                });

                map_layer = L.mapbox.tileLayer(playground.BASE_LAYER).addTo(map);
                grid_layer = L.mapbox.gridLayer(playground.BASE_LAYER).addTo(map);
                map.addControl(L.mapbox.gridControl(grid_layer));

                if (playground.fields.latitude.val() !== '' && playground.fields.latitude.val() !== 'None') {
                    map.setView([
                            playground.fields.latitude.val(),
                            playground.fields.longitude.val()],
                        playground.LOCATOR_DEFAULT_ZOOM);
                }
                playground.map.center_editor();
            },
            'center_editor': function() {
                map.off('moveend', playground.map.process_map_location);
                map.invalidateSize(false);
                var marker_left = $('#edit-map').width()/2 - 8;
                var marker_top = $('#edit-map').height()/2 - 8;
                $('#loading-spinner').hide();
                $('#edit-marker').css({'left': marker_left, 'top': marker_top}).show();
                map.on('moveend', playground.map.process_map_location);
            },
            'reset_editor': function() {
                if (playground.fields.latitude.val() !== '' && playground.fields.latitude.val() !== 'None') {
                    map.setView([
                            playground.fields.latitude.val(),
                            playground.fields.longitude.val()],
                        playground.LOCATOR_DEFAULT_ZOOM);
                }
            },
            'process_map_location': function() {
                var latlng = map.getCenter();
                playground.reverse_geocode(latlng.lat, latlng.lng, playground.callbacks.reverse_geocode);
            },
            'resize_locator': function() {
                // Set the width.
                playground.CONTENT_WIDTH = $('#main-content').width();
                playground.PAGE_WIDTH = $('body').outerWidth();

                // Set the map coords.
                var lat = playground.fields.latitude.val();
                var lon = playground.fields.longitude.val();
                var map_path;
                var map_height;
                var map_width = playground.CONTENT_WIDTH;
                var modal_path;
                var modal_width = $('#edit-playground').width();
                var modal_height;

                map_height = Math.floor(playground.CONTENT_WIDTH / 3);
                modal_height = Math.floor(modal_width / 3);

                if (playground.RETINA) {
                    map_width = map_width * 2;
                    if (map_width > 640) {
                        map_width = 640;
                    }
                    map_height = Math.floor(map_width / 3);
                }

                // Set up the map image.
                map_path = 'http://api.tiles.mapbox.com/v3/';
                map_path += playground.BASE_LAYER + '/pin-m-star+ff6633(' + lon + ',' + lat + ')/';
                map_path += lon + ',' + lat + ',' + playground.LOCATOR_DEFAULT_ZOOM + '/';
                modal_path = map_path;
                map_path += map_width + 'x' + map_height + '.png';
                modal_path += modal_width + 'x' + modal_height + '.png';

                playground.fields.locator_map.attr('src', map_path);
                playground.fields.modal_map.attr('src', modal_path);

                // Set the placeholder text.
                placeholder_text = playground.fields.address.val();
                placeholder_text += ' ' + playground.fields.city.val();
                placeholder_text += ', ' + playground.fields.state.val();
                $('#address-placeholder p').html(placeholder_text);
            }
        },
        'locate_me': function() {
            function success(position){
                map.setView([position.coords.latitude, position.coords.longitude], playground.LOCATOR_DEFAULT_ZOOM);
                playground.reverse_geocode(position.coords.latitude, position.coords.longitude, playground.callbacks.reverse_geocode);
                playground.fields.locator_map.removeClass('hidden');
            }

            function error(){
                $('#editor-tabs a:last').tab('show');
            }

            navigator.geolocation.getCurrentPosition(success, error);
        },
        'geocode': function(geocode_object, callback) {
            geocoder = new google.maps.Geocoder();
            geocoder.geocode({'address': geocode_object}, function(results, status) {
                if (status == google.maps.GeocoderStatus.OK && results[0]['partial_match'] !== true) {
                    console.log(results);
                    var locales = results[0]['address_components'];
                    var latlng = results[0]['geometry'];
                    callback(locales, latlng);
                }
                else {
                    alert_text = "<h3>We're sorry!</h3>We're having a hard time finding this place.";
                    make_alert(alert_text, 'warning', 'div.alerts');
                }
            })
        },
        'reverse_geocode': function(latitude, longitude, callback) {
            geocoder = new google.maps.Geocoder();
            var latlng = new google.maps.LatLng(latitude, longitude);
            if (geocoder) {
                geocoder.geocode({'latLng': latlng}, function(results, status) {
                    if (status == google.maps.GeocoderStatus.OK) {
                        var locales = results[0]['address_components'];
                        callback(locales, latlng);
                    }
                    else {
                        alert_text = "<h3>We're sorry!</h3>We're having a hard time finding this place.";
                        make_alert(alert_text, 'warning', 'div.alerts');
                    }
                });
            };
        },
        'accept_address': function() {
            var has_street_address = playground.fields.address.val() !== '';
            var has_city = playground.fields.address.val() !== '';
            var has_state = playground.fields.state.val() !== '';
            var has_zip = playground.fields.address.val() !== '';
            var use_city_state = has_street_address && has_city && has_state;
            var use_zip = has_street_address && has_zip;

            if (!(use_city_state || use_zip)) {
                alert_text = "<strong>We're sorry!</strong><br>We need more information to find this location. Please provide an address with a city and state or ZIP code.";
                make_alert(alert_text, 'alert-error', 'div.alerts');
                return;
            }

            if (playground.fields.reverse_geocoded.attr('checked') !== 'checked'){
                playground.geocode(playground.form.prepare_geocode_object(), playground.callbacks.geocode);
            } else {
                this.hide_address_editor();
            }
        },
        'toggle_address_editor': function(){
            if (this.fields.address_editor.hasClass('hide')){
                this.show_address_editor();
            } else {
                this.hide_address_editor();
            }
        },
        'show_address_editor': function(){
            this.fields.address_editor.removeClass('hide');
            this.fields.address_editor_toggle.text('Cancel');
            this.map.center_editor();
            if ($('body').hasClass('create-playground')){
                $('.modal-backdrop').toggleClass('in');
            }
        },
        'hide_address_editor': function(){
            if ($('body').hasClass('create-playground')){
                $('.modal-backdrop').toggleClass('in');
            }
            this.fields.address_editor.addClass('hide');
            this.fields.address_editor_toggle.text('Edit');

            $('#editor-tabs a:first').tab('show');
        },
        'reset_form': function() {
            $('#edit-playground').modal('hide');
            $.each(this.inputs.text_input, function(){
                $this = $(this);
                $this.val($this.data('original')).attr('data-changed', 'false');
            });
            $.each(this.inputs.checkbox, function(){
                $this = $(this);
                $this.prop('checked', $this.data('original')).attr('data-changed', 'false');
            });
            this.map.resize_locator();
            this.map.reset_editor();
        },
        'reset_location': function(){
            this.hide_address_editor();
            if(playground.address_change_accepted !== true){
                var field_list = [
                    'address',
                    'city',
                    'zip_code',
                    'latitude',
                    'longitude',
                    'reverse_geocoded',
                    'state'
                ];

                $.each(field_list, function(index, field_name){
                    var field = $('input[name="' + field_name + '"], select[name="' + field_name + '"]');
                    field.val(field.data('original')).attr('data-changed', 'false');
                });
                this.map.resize_locator();
                this.map.reset_editor();
            }
        },
        'submit': function() {
            if ( playground.fields.reverse_geocoded.attr('checked') !== 'checked' ) {
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

            // Store original values as data attribute
            $.each(playground.inputs.text_input, function(){
                var $this = $(this);
                $this.attr('data-original', $this.val());
            });

            $.each(playground.inputs.checkbox, function(){
                var $this = $(this);
                $this.attr('data-original', $this.is(':checked'));
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

            if(playground.fields.latitude.val() === '' || playground.fields.latitude.val() === 'None'){
                var latitude = get_parameter_by_name('latitude');
                var longitude = get_parameter_by_name('longitude');

                if (latitude) {
                    playground.fields.latitude.val(latitude);
                }

                if (longitude) {
                    playground.fields.longitude.val(longitude);
                }

                if (latitude && longitude) {
                    playground.reverse_geocode(latitude, longitude, playground.callbacks.reverse_geocode);
                } else {
                    playground.locate_me();
                }
            }

            // Set up the map.
            playground.map.setup();

            // Watch the map.
            // Perform a reverse geocode when the map is finished moving.
            map.on('moveend', playground.map.process_map_location);

            // Sets up the click functions for each of the buttons.
            // Requires a data-action attribute on the button element.
            $('#form .btn').each(function(index, action){
                $(this).on('click', function(){
                    playground[$(this).attr('data-action')]($(this).attr('data-path'));
                    return false;
                });
            });

            // Allow users to tab feature labels and descriptions to toggle checkbox
            $('#form .feature').find('label, .help-block, img').each(function(){
                $(this).on('click', function() {
                    var input_checked = $(this).siblings('input').prop('checked');
                    $(this).siblings('input').prop('checked', !input_checked);
                });
            });

            // Watch for changes to the playground form.
            $('#form .input').blur(function(){

                // Set a changed attribute.
                $(this).attr('data-changed', 'true');

                // Remove a validation flag, if it exists.
                $(this).removeClass('flagged');
            });

            $('#address-pane input, #address-pane select').blur(function(){
                playground.fields.reverse_geocoded.removeAttr('checked');
            })

            // Check to see if we've got a message to show.
            if (playground.ACTION !== null){
                // We'll name the message div after the URL param.
                $('#' + playground.ACTION).toggleClass('hide');
            }


            // Do this thing with the map.
            if ( $('#locator-map') ) {
                playground.map.resize_locator();
                $(window).resize(_.debounce(playground.map.resize_locator_map, 100));
            }

            // Need to recenter the editor if the map dimension changes
            if ( $('#edit-map') ) {
                $(window).resize(_.debounce(playground.map.center_editor, 100));
            }

            // Recenter the editor map when you activate the map pane
            $('#editor-tabs a:first').on('click', function(e){
                e.preventDefault();
                $('this').tab('show');
                setTimeout(playground.map.center_editor, 25);
            })

            // All of this meta_hdr and meta_items stuff.
            playground.form.twist_out(playground.fields.meta_hdr, playground.fields.meta_items);
            playground.form.twist_out(playground.fields.meta_comments, playground.fields.meta_guidelines);
            playground.form.twist_out(playground.fields.meta_changelog, playground.fields.meta_changes);
        }
    };
    // Initialize the playground object.
    playground.setup();
});
