$(function() {
    var playground = {
        "ACTION": get_parameter_by_name('action'),
        "BASE_LAYER": APP_CONFIG.MAPBOX_BASE_LAYER,
        "CONTENT_WIDTH": 0,
        "GEOLOCATE": Modernizr.geolocation,
        "LOCATOR_DEFAULT_ZOOM": 15,
        "PAGE_WIDTH": 0,
        "RESULTS_MAP_WIDTH": 500,
        "RESULTS_MAP_HEIGHT": 500,
        "RESULTS_MAX_ZOOM": 16,
        "RESULTS_MIN_ZOOM": 8,
        "RESULTS_DEFAULT_ZOOM": 14,
        "RETINA": window.devicePixelRatio > 1,
        "fields": {
            // Many other fields are set dynamically.
            "locator_map": $('#locator-map'),
            "modal_map": $('#modal-locator-map'),
            "meta_items": $('#main-content').find('.about').find('ul.meta'),
            "meta_hdr": $('#main-content').find('.about').find('h5.meta')
        },
        "callbacks": {
            "geocode": function(locale) {
                this.fields.latitude.attr('value', locale['latLng']['lat']);
                this.fields.longitude.attr('value', locale['latLng']['lng']);
                require_us_address(locale);
                this.form.geocode_fields();
                $('#form').submit();
            },
            "reverse_geocode": function(locale) {
                this.fields.address.val(locale['street']);
                this.fields.city.val(locale['adminArea5']);
                this.fields.state.val(locale['adminArea3']);
                this.fields.zip_code.val(locale['postalCode']);
                this.fields.latitude.val(locale['latLng']['lat']);
                this.fields.longitude.val(locale['latLng']['lng']);
            }
        },
        "form": {
            "submit": function() {
                if ( this.fields.reverse_geocode.attr('checked') !== 'checked' ) {
                    this.geocode(this.form.prepare_geocode_string(), this.callbacks.geocode);
                } else {
                    this.form.geocode_fields();
                    this.fields.reverse_geocoded.attr('checked', 'checked');
                    this.fields.reverse_geocoded.attr('data-changed', 'true');
                    $('#form').submit();
                }
                return false;
            },
            "validate": function() {
                var required_fields = $('#form input[data-required="true"]');
                var flagged_fields = [];
                $.each(required_fields, function(index, required_field){
                    if (required_field.val === '') {
                        flagged_fields.push(required_field);
                    }
                });
                if (flagged_fields.length > 0){
                    this.form.flag_fields(flagged_fields);
                    return false;
                } else {
                    return true;
                }

            },
            "flag_fields": function(flagged_fields) {
                $(required_field).addClass('flagged');
            },
            "prepare_geocode_string": function() {
                var geocode_string = this.address.val();
                geocode_string += ' ' + this.city.val();
                geocode_string += ', ' + this.state.val();
                return geocode_string + ' ' + this.zip_code.val();
            },
            "geocode_fields": function() {
                // Set the base location fields to "changed" so that they will POST.
                this.fields.address.attr('data-changed', 'true');
                this.fields.city.attr('data-changed', 'true');
                this.fields.state.attr('data-changed', 'true');
                this.fields.zip_code.attr('data-changed', 'true');
                this.fields.latitude.attr('data-changed', 'true');
                this.fields.longitude.attr('data-changed', 'true');

                // Try to set the state to a proper state name.
                this.fields.state.val(STATE_NAME_TO_CODE[this.fields.state.val()]);

                // Reset the locator map.
                this.fields.locator_map.data('latitude', this.fields.latitude.val());
                this.fields.locator_map.data('longitude', this.fields.longitude.val());
                this.map.resize_locator();
            }
        },
        "map": {
            "init": function() {
                /*
                * Initializes the map.
                */
                map = L.map('edit-map', {
                    minZoom: 11,
                    scrollWheelZoom: false
                });

                map_layer = L.mapbox.tileLayer(this.BASE_LAYER).addTo(map);
                grid_layer = L.mapbox.gridLayer(this.BASE_LAYER).addTo(map);
                map.addControl(L.mapbox.gridControl(grid_layer));

                if (this.fields.latitude.val() !== '' && this.fields.longitude.val() !== '') {
                    map.setView([
                            this.fields.latitude.val(),
                            this.fields.longitude.val()],
                        this.LOCATOR_DEFAULT_ZOOM);
                } else {
                    map.setView([38.9, -77], 12);
                }
                console.log(map);
                this.map.center_editor();
            },
            "center_editor": function() {
                map.invalidateSize(false);
                var marker_left = $('#edit-map').width()/2 - 8;
                var marker_top = $('#edit-map').height()/2 - 8;
                $('#edit-marker').css({'left': marker_left, 'top': marker_top});
            },
            "resize_locator": function() {
                this.CONTENT_WIDTH = $('#main-content').width();
                this.PAGE_WIDTH = $('body').outerWidth();
                var lat = this.fields.locator_map.data('latitude');
                var lon = this.fields.locator_map.data('longitude'); // Because iOS refuses to obey toString()
                var map_path;
                var new_height;
                var new_width = this.CONTENT_WIDTH;

                if (this.PAGE_WIDTH > 480) {
                    new_width = Math.floor(new_width / 2) - 22;
                }
                new_height = Math.floor(this.CONTENT_WIDTH / 3);

                if (this.RETINA) {
                    new_width = new_width * 2;
                    if (new_width > 640) {
                        new_width = 640;
                    }
                    new_height = Math.floor(new_width / 3);
                }

                map_path = 'http://api.tiles.mapbox.com/v3/' + this.BASE_LAYER + '/pin-m-star+ff6633(' + lon + ',' + lat + ')/' + lon + ',' + lat + ',' + this.LOCATOR_DEFAULT_ZOOM + '/' + new_width + 'x' + new_height + '.png';
                this.fields.locator_map.attr('src', map_path);
                this.fields.modal_map.attr('src', map_path);
            }
        },
        "locate_me": function() {
            navigator.geolocation.getCurrentPosition(function(position) {
                map.setView([position.coords.latitude, position.coords.longitude], this.LOCATOR_DEFAULT_ZOOM);
                this.reverse_geocode(position.coords.latitude, position.coords.longitude, this.callbacks.reverse_geocode);
            });
        },
        "activate_path": function(path) {
            $('#form .path').hide();
            $('.' + path).show();
            this.map.center_editor();
            if ( $(this).attr('data-reverse-geocode') === 'checked' ) {
                this.fields.reverse_geocode.attr('checked', 'checked');
            }
        },
        "geocode": function(address_string, callback) {
            $.ajax({
                'url': 'http://open.mapquestapi.com/geocoding/v1/?inFormat=kvp&location=' + address_string,
                'dataType': 'jsonp',
                'contentType': 'application/json',
                'success': function(data) {
                    var locales = data['results'][0]['locations'];
                    var locale = locales[0];
                    var zip_list = [];
                    callback(locale);
                }
            });
        },
        "reverse_geocode": function(latitude, longitude, callback) {
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
        "init": function() {
            // Set all of the playground field names.
            // List of fields we'd like to set up.
            var field_list = [
                "address",
                "city",
                "state",
                "zip_code",
                "latitude",
                "longitude",
                "reverse_geocoded"];

            // Loop and add a playgrounds.field attribute for each of these fields.
            $.each(field_list, function(index, field_name){
                this.fields[field_name] = $('input[name="' + field_name + '"]');
            });

            // Set up the screen width constants.
            this.CONTENT_WIDTH = $('#main-content').width();
            this.PAGE_WIDTH = $('body').outerWidth();
            this.RESULTS_MAP_WIDTH = this.CONTENT_WIDTH;
            this.RESULTS_MAP_HEIGHT = this.CONTENT_WIDTH;
            if (this.RETINA) {
                this.BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER_RETINA;
                this.LOCATOR_DEFAULT_ZOOM += 1;
                this.RESULTS_DEFAULT_ZOOM += 1;
            }

            // Set up the map.
            this.map.init();

            // Watch the map.
            // Perform a reverse geocode when the map is finished moving.
            map.on('moveend', function() {
                var latlng = map.getCenter();
                this.reverse_geocode(latlng.lat, latlng.lng, this.callbacks.reverse_geocode);
            });

            // Activate the default geocode path. In this case, the map?
            this.activate_path('path-1');

            // Sets up the click functions for each of the buttons.
            // Requires a data-action attribute on the button element.
            $('#form a.btn').each(function(index, action){
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
            if (this.ACTION !== null){

                // We'll name the message div after the URL param.
                $('#' + this.ACTION).toggleClass('hide');
            }

            // Set up the features tooltip.
            $('.playground-features i').tooltip( { trigger: 'click' } );

            // Do this thing with the map.
            if ( $('#locator-map') ) {
                this.map.resize_locator();
                $(window).resize(_.debounce(this.map.resize_locator_map, 100));
            }

            // All of this meta_hdr and meta_items stuff.
            this.fields.meta_hdr.html(this.fields.meta_hdr.html() + ' &rsaquo;');
            this.fields.meta_items.hide();
            this.fields.meta_hdr.on('click', function() {
                this.fields.meta_items.slideToggle('fast');
            });

        }
    };

    // Initialize the playground object.
    this.init();
});
