var BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER;
var CONTENT_WIDTH;
var GEOLOCATE = Modernizr.geolocation;
var LOCATOR_DEFAULT_ZOOM = 15;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 8;
var RESULTS_DEFAULT_ZOOM = 15;
var IS_MOBILE = Modernizr.touch;
var RETINA = window.devicePixelRatio > 1;
if (RETINA) {
    BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER_RETINA;
    LOCATOR_DEFAULT_ZOOM += 1;
    RESULTS_DEFAULT_ZOOM += 1;
}

var LETTERS = 'abcdefghijklmnopqrstuvwxyz';

var $search_form = null;
var $search_address = null;
var $search_divider = null;
var $search_latitude = null;
var $search_longitude = null;
var $geolocate_button = null;
var $search_results_wrapper = null;
var $search_results = null;
var $search_results_ul = null;
var $search_results_map_wrapper = null;
var $search_results_map = null;
var $search_results_map_loading = null;
var $search_results_map_loading_text = null;
var $zoom_in = null;
var $zoom_out = null;
var $did_you_mean_wrapper = null;
var $did_you_mean = null;
var $search_help_prompt = null;
var $results_address = null;
var $no_geocode = null;
var $map_loading = null;
var $results_loading = null;
var $playground_meta_hdr = null;
var $playground_meta_items = null;

var zoom = RESULTS_DEFAULT_ZOOM;
var crs = null;
var desktop_map = null;
var desktop_markers = null;
var $selected_playground = null;
var search_xhr = null;
var geocode_xhr = null;
var user_zoomed = false;

function degToCloudSearch(degree) {
    /*
     * Convert a degree of lat or lon to our CloudSearch uint representation.
     */
    return parseInt((degree + APP_CONFIG.CLOUD_SEARCH_DEG_OFFSET) * APP_CONFIG.CLOUD_SEARCH_DEG_SCALE);
}

function cloudSearchToDeg(uint) {
    /*
     * Convert a CloudSearch uint into a degree of lat or lon.
     */
    return parseFloat((uint / APP_CONFIG.CLOUD_SEARCH_DEG_SCALE) - APP_CONFIG.CLOUD_SEARCH_DEG_OFFSET);
}

function buildCloudSearchParams() {
    /*
     * Reads the current state of the UI and builds appropraite CloudSearch query params.
     */
    var deployment_target = (APP_CONFIG.DEPLOYMENT_TARGET || 'staging');
    //var query = $search_query.val();
    var latitude = parseFloat($search_latitude.val());
    var longitude = parseFloat($search_longitude.val());

    var params = {};
    var return_fields = ['name', 'display_name', 'city', 'state', 'latitude', 'longitude', 'public_remarks', 'slug'];

    for (feature in window.FEATURES) {
        return_fields.push('feature_' + feature.replace(/-/g, '_'));
    }

    var query_bits = ['deployment_target:\'' + deployment_target + '\''];

    /*if (query) {
        query_bits.push('full_text:\'' + query + '\'');
    }*/

    // If using geosearch
    if (latitude) {
        // Generate bounding box for map viewport
        var point = crs.latLngToPoint(new L.LatLng(latitude, longitude), zoom);
        var upper_left = point.subtract([RESULTS_MAP_WIDTH / 2, RESULTS_MAP_HEIGHT / 2]);
        var lower_right = point.add([RESULTS_MAP_WIDTH / 2, RESULTS_MAP_HEIGHT / 2]);
        var northwest = crs.pointToLatLng(upper_left, zoom);
        var southeast = crs.pointToLatLng(lower_right, zoom);

        query_bits.push('longitude:' + degToCloudSearch(northwest.lng) + '..' + degToCloudSearch(southeast.lng) + ' latitude:' + degToCloudSearch(southeast.lat) + '..' + degToCloudSearch(northwest.lat));

        var latitude_radians = degToRad(latitude);
        var longitude_radians = degToRad(longitude);
        var offset = APP_CONFIG.CLOUD_SEARCH_DEG_OFFSET;
        var scale = APP_CONFIG.CLOUD_SEARCH_DEG_SCALE;

        // Compile ranking algorithm (spherical law of cosines)
        // Note results are scaled up by 1000x.
        var rank_distance = '3958.761 * Math.acos(Math.sin(' + latitude_radians + ') * Math.sin(((latitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) + Math.cos(' + latitude_radians + ') * Math.cos(((latitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) * Math.cos((((longitude / ' + scale + ') - ' + offset + ') * 3.14159 / 180) - ' + longitude_radians + ')) * 1000';

        params['rank'] = 'distance';
        params['rank-distance'] = rank_distance;

        return_fields.push('distance');
    } else {
        params['rank'] = 'name';
    }

    params['bq'] = '(and ' + query_bits.join(' ') + ')';
    params['return-fields'] = return_fields.join(',');
    params['size'] = 26;

    return params;
}

function buildMapboxPin(size, shape, color, lat, lng) {
    /*
     * Generate the URL format for a mapbox static pin.
     */
    return 'pin-' + size + '-' + shape + '+' + color + '(' + lng + ',' + lat + ')';
}

function search() {
    /*
     * Execute a search using current UI state.
     */
    var latitude = parseFloat($search_latitude.val());
    var longitude = parseFloat($search_longitude.val());

    $search_results_ul.empty();
    $search_help_prompt.hide();
    $selected_playground = null;

    if (IS_MOBILE) {
        $search_results_map_loading.show();
        $search_results_map_loading_text.show();
        $search_results_map.css('opacity', '0.25');
    } else {
        desktop_map.removeLayer(desktop_markers);
    }

    if (search_xhr != null) {
        search_xhr.abort();
    }

    search_xhr = $.ajax({
        url: APP_CONFIG.CLOUD_SEARCH_PROXY_BASE_URL + '/cloudsearch/2011-02-01/search?' + $.param(buildCloudSearchParams()),
        dataType: 'jsonp',
        complete: function() {
            search_xhr = null;
        },
        success: function(data) {
            $map_loading.hide();
            $results_loading.hide();

            var markers = [];

            if (data['hits']['hit'].length > 0) {
                _.each(data['hits']['hit'], function(hit, i) {
                    var context = $.extend(APP_CONFIG, hit);
                    context['letter'] = LETTERS[i];

                    var html = JST.playground_item(context);
                    $search_results_ul.append(html);

                    if (hit.data.latitude.length > 0) {
                        var lat = cloudSearchToDeg(hit.data.latitude[0]);
                        var lng = cloudSearchToDeg(hit.data.longitude[0]);

                        if (IS_MOBILE) {
                            markers.push(buildMapboxPin('m', context['letter'], 'ff6633', lat, lng));
                        } else {
                            var marker = L.mapbox.marker.style({
                                'type': 'Feature',
                                'geometry': {},
                                'properties': {
                                    'marker-size': 'medium',
                                    'marker-symbol': context['letter'],
                                    'marker-color': '#ff6633'
                                }
                            }, [lat, lng]);

                            marker.letter = context['letter'];

                            marker.on('mouseover', function() {
                                $('.playground-list li').removeClass('highlight');
                                $('#playground-' + this.letter).addClass('highlight');
                                
                                if ($selected_playground) {
                                    $selected_playground.addClass('highlight');
                                }
                            });

                            marker.on('mouseout', function() {
                                $('.playground-list li').removeClass('highlight');
                                
                                if ($selected_playground) {
                                    $selected_playground.addClass('highlight');
                                }
                            });

                            marker.on('click', function() {
                                $selected_playground = $('#playground-' + this.letter);

                                $('.playground-list li').removeClass('highlight');
                                $selected_playground.addClass('highlight');
                                
                                $.smoothScroll({ scrollTarget: '#playground-' + this.letter });
                            });

                            markers.push(marker);
                        }
                    }
                });
            } else {
                if (!user_zoomed) {
                    if (zoom == 15) {
                        zoom = 11;

                        if (IS_MOBILE) {
                            $search_results_map_loading.show();
                            $search_results_map_loading_text.text('Searching further away...').show();
                            $search_results_map.css('opacity', '0.25');
                        } else {
                            $map_loading.text('Searching further away...').show();
                        }

                        search();
                    } else if (zoom == 11) {
                        zoom = 8;
                        
                        if (IS_MOBILE) {
                            $search_results_map_loading.show();
                            $search_results_map_loading_text.text('Searching far away...').show();
                            $search_results_map.css('opacity', '0.25');
                        } else {
                            $map_loading.text('Searching far away...').show();
                        }

                        $zoom_out.attr('disabled', 'disabled');
                        search();
                    } else {
                        $search_results_ul.append('<li class="no-results">No playgrounds found</li>');
                    }
                } else {
                    $search_results_ul.append('<li class="no-results">No playgrounds found</li>');
                }
            }

            if (latitude) {
                if (IS_MOBILE) {
                    var search_map_width = RESULTS_MAP_WIDTH;
                    var search_map_height = RESULTS_MAP_HEIGHT;

                    if (RETINA) {
                        search_map_width = search_map_width * 2;
                        search_map_height = search_map_height * 2;

                        if (search_map_width > 640) {
                            search_map_width = 640;
                        }

                        if (search_map_height > 640) {
                            search_map_height = 640;
                        }
                    }

                    markers.push(buildMapboxPin('l', 'circle', '006633', latitude, longitude));

                    $search_results_map.on('load', function() {
                        $search_results_map_loading.hide();
                        $search_results_map_loading_text.text('Searching...').hide();
                        $search_results_map.css('opacity', '1.0');
                        $search_results_map.off('load');
                    });

                    $search_results_map.attr('src', 'http://api.tiles.mapbox.com/v3/' + BASE_LAYER + '/' + markers.join(',') + '/' + longitude + ',' + latitude + ',' + zoom + '/' + search_map_width + 'x' + search_map_height + '.png');
                } else {
                    desktop_map.setView([latitude, longitude], zoom);

                    desktop_markers.clearLayers();

                    markers.push(L.mapbox.marker.style({
                        'type': 'Feature',
                        'geometry': {},
                        'properties': {
                            'marker-size': 'large',
                            'marker-symbol': 'circle',
                            'marker-color': '#006633'
                        }
                    }, [latitude, longitude]));

                    _.each(markers, function(marker) {
                        desktop_markers.addLayer(marker);
                    });
                    
                    desktop_map.addLayer(desktop_markers);
                }

                $search_results_map_wrapper.show();
                $results_address.show();
            }

            $search_results.show();
            $search_help_prompt.show();

            if (!IS_MOBILE) {
                desktop_map.invalidateSize();
            }

            $.smoothScroll({ scrollTarget: '#results-address' });
        },
        cache: true
    });
}

function navigate(nearby) {
    /*
     * Update the url hash, triggering the page to change.
     */
    // Maintain nearby value if unspecified
    if (_.isUndefined(nearby)) {
        nearby = $.bbq.getState('nearby') == 'true';
    }

    $.bbq.pushState({
        'address': $search_address.val(),
        'latitude': $search_latitude.val(),
        'longitude': $search_longitude.val(),
        'zoom': zoom,
        'nearby': nearby
    })
}

function reset_zoom() {
    /*
     * Reset zoom level to default.
     */
    zoom = RESULTS_DEFAULT_ZOOM;
    $zoom_in.removeAttr('disabled');
    $zoom_out.removeAttr('disabled');

    user_zoomed = false;
}

function hashchange_callback() {
    /*
     * React to changes in the url hash and update the search.
     */
    var address = $.bbq.getState('address') || '';
    $search_address.val(address);
    var latitude = $.bbq.getState('latitude');
    var longitude = $.bbq.getState('longitude');
    zoom = parseInt($.bbq.getState('zoom')) || zoom;
    var nearby = ($.bbq.getState('nearby') == 'true') || false;

    if (latitude && longitude) {
        if (!($search_latitude.val() == latitude && $search_longitude.val() == longitude)) {
            $did_you_mean_wrapper.hide();
            $search_results_ul.empty();
            $results_address.hide();
        }

        $search_latitude.val(latitude);
        $search_longitude.val(longitude);

        if (!nearby) {
            $results_address.text('Showing Results Near ' + $search_address.val());
        } else {
            $results_address.text('Showing Results Near You');
        }

        $results_loading.show();

        search();
    } else if (address) {
        $search_form.submit();
    }
}

$(function() {
    $search_form = $('#search');
    $search_address = $('#search input[name="address"]');
    $search_again = $('#search-again');
    $search_divider = $search_form.find('h6.divider');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_results = $('#search-results');
    $search_results_ul = $search_results.find('ul');
    $search_results_map_wrapper = $('#search-results-map-wrapper');
    $search_results_map_desktop = $('#search-results-map-desktop');
    $search_results_map = $('#search-results-map');
    $search_results_map_loading = $('#search-results-map-loading');
    $search_results_map_loading_text = $('#search-results-map-loading-text');
    $zoom_in = $('#zoom-in');
    $zoom_out = $('#zoom-out');
    $did_you_mean_wrapper = $('#search-help');
    $did_you_mean = $('#search-help ul');
    $search_help_prompt = $('#search-help-prompt');
    $results_address = $('#results-address');
    $no_geocode = $('#no-geocode');
    $map_loading = $('#map-loading');
    $results_loading = $('#results-loading');
    $playground_meta_hdr = $('#main-content').find('.about').find('h5.meta');
    $playground_meta_items = $('#main-content').find('.about').find('ul.meta');
    $alerts = $('.alerts');

    CONTENT_WIDTH = $('#main-content').width();
    SEARCH_WIDTH = $('#main-content').find('.span6:eq(1)').width();
    RESULTS_MAP_WIDTH = SEARCH_WIDTH;
    RESULTS_MAP_HEIGHT = SEARCH_WIDTH;

    crs = L.CRS.EPSG3857;

    // Fetches the key from the URL. This could easily be undefined or null.
    var action = get_parameter_by_name('action');
    if (action !== null){
        // We'll name the message div after the URL param.
        $('#' + action).toggleClass('hide');
    }

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(function(position) {
            $search_address.val('');
            $search_latitude.val(position.coords.latitude);
            $search_longitude.val(position.coords.longitude);

            reset_zoom();

            navigate(true);
        }
        );

        return false;
    });

    $zoom_in.click(function() {
        zoom += 1;

        if (zoom == RESULTS_MAX_ZOOM) {
            $zoom_in.attr('disabled', 'disabled');
        }

        $zoom_out.removeAttr('disabled');

        user_zoomed = true;

        navigate();

        return false;
    });

    $zoom_out.click(function() {
        zoom -= 1;

        if (zoom == RESULTS_MIN_ZOOM) {
            $zoom_out.attr('disabled', 'disabled');
        }

        $zoom_in.removeAttr('disabled');

        user_zoomed = true;

        navigate();

        return false;
    });

    $did_you_mean.on('click', 'li', function() {
        var $this = $(this);
        var display_name = $this.data('display-name');
        var latitude = $this.data('latitude');
        var longitude = $this.data('longitude');

        $search_address.val(display_name);
        $search_latitude.val(latitude);
        $search_longitude.val(longitude);
        $results_address.html('Showing Results Near ' + display_name);

        $did_you_mean_wrapper.hide();

        $map_loading.show();
        $map_loading.text('Searching...');
        navigate(false);

        return false;
    });

    $search_form.submit(function() {
        if ($search_address.val() === '') {
            return false;
        }

        $did_you_mean_wrapper.hide();
        $search_help_prompt.hide();
        $search_results_ul.empty();
        $search_results_map_wrapper.hide();
        $results_address.hide();
        $no_geocode.hide();

        reset_zoom();

        var address = $search_address.val();

        if (address) {
            $map_loading.show();

            if (geocode_xhr) {
                geocode_xhr.cancel();
            }

            geocode_xhr = $.ajax({
                'url': 'http://open.mapquestapi.com/nominatim/v1/search.php?format=json&json_callback=playgroundCallback&q=' + address,
                'type': 'GET',
                'dataType': 'jsonp',
                'cache': true,
                'jsonp': false,
                'jsonpCallback': 'playgroundCallback',
                'contentType': 'application/json',
                'complete': function() {
                    geocode_xhr = null;
                },
                'success': function(data) {
                    // US addresses only, plzkthxbai.
                    data = _.filter(data, function(locale) {
                        return locale['display_name'].indexOf("United States of America") > 0;
                    });

                    $map_loading.hide();

                    if (data.length === 0) {
                        // If there are no results, show a nice message.
                        $did_you_mean.append('<li>No results</li>');
                        $no_geocode.show();
                    } else if (data.length == 1) {
                        // If there's one result, render it.
                        var locale = data[0];

                        var display_name = locale['display_name'].replace(', United States of America', '');
                        $search_latitude.val(locale['lat']);
                        $search_longitude.val(locale['lon']);
                        $search_address.val(display_name);

                        $results_address.html('Showing Results Near ' + display_name);

                        $map_loading.text('Searching...').show();

                        navigate(false);
                    } else {
                        // If there are many results,
                        // show the did-you-mean path.
                        $did_you_mean.empty();

                        _.each(data, function(locale) {
                            locale['display_name'] = locale['display_name'].replace(', United States of America', '');
                            var context = $.extend(APP_CONFIG, locale);
                            var html = JST.did_you_mean_item(context);

                            $did_you_mean.append(html);

                        });

                        $did_you_mean_wrapper.show();
                    }
                }
            });
        } else {
            $search_latitude.val('');
            $search_longitude.val('');
            $map_loading.text('Searching...').show();
            navigate();
        }

        return false;
    });

    if (GEOLOCATE) {
        $geolocate_button.show();
        $search_divider.show();
    }

    if (!IS_MOBILE) {
        $search_results_map_desktop.css({ height: '500px' });

        desktop_map = L.mapbox.map('search-results-map-desktop', null, {
            zoomControl: false,
            scrollWheelZoom: false
        });

        desktop_map.on('moveend', function() {
            var latlng = desktop_map.getCenter();
            var current = new L.LatLng($search_latitude.val(), $search_longitude.val());
            zoom = desktop_map.getZoom();

            if (!coordinatesApproxEqual(latlng, current, 100)) {
                $search_latitude.val(latlng.lat);
                $search_longitude.val(latlng.lng);

                navigate();
            }
        });

        var tiles = L.mapbox.tileLayer('npr.map-s5q5dags', {
            detectRetina: true,
            retinaVersion: 'npr.map-u1zkdj0e',
        });

        tiles.addTo(desktop_map);

        desktop_markers = L.layerGroup();
    }

    // Check to see if we've got a message to show.
    if (get_parameter_by_name('action') !== null){
        // We'll name the message div after the URL param.
        $('#' + get_parameter_by_name('action')).toggleClass('hide').show();
    }

    $(window).bind('hashchange', hashchange_callback);
    $(window).trigger('hashchange');
});
