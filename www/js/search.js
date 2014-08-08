var BASE_LAYER = APP_CONFIG.MAPBOX_BASE_LAYER;
var CONTENT_WIDTH;
var PAGE_WIDTH;
var GEOLOCATE = Modernizr.geolocation;
var RESULTS_MAP_WIDTH = 500;
var RESULTS_MAP_HEIGHT = 500;
var RESULTS_MAX_ZOOM = 16;
var RESULTS_MIN_ZOOM = 8;
var IS_MOBILE = Modernizr.touch;

var LETTERS = 'abcdefghijklmnopqrstuvwxyz';

var $search_form = null;
var $search_address = null;
var $search_divider = null;
var $search_help_message = null;
var $search_latitude = null;
var $search_longitude = null;
var $geolocate_button = null;
var $search_results_wrapper = null;
var $search_results = null;
var $search_results_ul = null;
var $search_results_map_wrapper = null;
var $search_results_map = null;
var $search_results_map_loading_text = null;
var $search_results_not_found = null;
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
var $create_link = null;

var zoom = RESULTS_DEFAULT_ZOOM;
var desktop_map = null;
var desktop_markers = null;
var $selected_playground = null;
var search_xhr = null;
var geocode_xhr = null;
var user_zoomed = false;
var user_panned = false;
var move_end_listener = null;
var markers = [];


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
    console.log($create_link.attr('href'));
    $create_link.attr('href', 'create.html?latitude=' + latitude + '&longitude=' + longitude);
    console.log($create_link.attr('href'));



    var latlng = new google.maps.LatLng(latitude, longitude);
    var not_found = false;

    $search_results_ul.empty();
    $search_results_not_found.hide();
    $search_help_prompt.hide();
    $selected_playground = null;
    $search_help_message.hide();

    if (IS_MOBILE) {
        $search_results_map_loading_text.show();
        $search_results_map.css('opacity', '0.25');
    } else {
        for (var i=0; i < markers.length; i++) {
            markers[i].setMap(null);
        }
    }

    if (search_xhr !== null) {
        search_xhr.abort();
    }

    search_xhr = $.ajax({
        url: APP_CONFIG.CLOUD_SEARCH_PROXY_BASE_URL + '/cloudsearch/2011-02-01/search?' + $.param(buildCloudSearchParams(latitude, longitude, zoom)),
        dataType: 'jsonp',
        tryCount: 0,
        retryLimit: 3,
        retryDelay: 1000,
        complete: function() {
            search_xhr = null;
        },
        success: function(data) {
            if ('error' in data) {
                this.tryCount += 1;

                if (this.tryCount < this.retryLimit) {
                    // Trim jquery callback as the retry is going to add another one
                    var i = this.url.indexOf('callback=');
                    this.url = this.url.substring(0, i - 1);

                    xhr = this;

                    window.setTimeout(function() {
                        search_xhr = $.ajax(xhr);
                    }, this.retryDelay);

                    return;
                }

                alert('Our search feature is currently over capacity, please try again later.');

                return;
            }

            $map_loading.hide();
            $results_loading.hide();

            if (!IS_MOBILE) {
                for (var i=0; i < markers.length; i++) {
                    markers[i].setMap(null);
                }
            }

            markers = [];

            if (data['hits']['hit'].length > 0) {
                _.each(data['hits']['hit'], function(hit, i) {
                    var context = $.extend(APP_CONFIG, hit);
                    context['letter'] = LETTERS[i];

                    context['features'] = [];

                    // Generate a list of included features
                    for (var feature in window.FEATURES) {
                        var key = 'feature_' + feature.replace(/-/g, '_');

                        if (hit['data'][key][0] > 0) {
                            context['features'].push(window.FEATURES[feature]);
                        }
                    }

                    var html = JST.playground_item(context);
                    $search_results_ul.append(html);

                    if (hit.data.latitude.length > 0) {
                        var lat = cloudSearchToDeg(hit.data.latitude[0]);
                        var lng = cloudSearchToDeg(hit.data.longitude[0]);

                        if (IS_MOBILE) {
                            markers.push(buildMapboxPin('m', context['letter'], 'ff6633', lat, lng));
                        } else {
                            var marker = new google.maps.Marker({
                                map: google_desktop_map,
                                position: new google.maps.LatLng(lat, lng),
                                icon: "http://maps.google.com/mapfiles/marker" + context['letter'].toUpperCase() + ".png",
                            });

                            var letter = context['letter'];

                            google.maps.event.addListener(marker, 'mouseover', function() {
                                $('.playground-list li').removeClass('highlight');
                                $('#playground-' + letter).addClass('highlight');

                                if ($selected_playground) {
                                    $selected_playground.addClass('highlight');
                                }
                            });

                            google.maps.event.addListener(marker, 'mouseout', function() {
                                $('.playground-list li').removeClass('highlight');

                                if ($selected_playground) {
                                    $selected_playground.addClass('highlight');
                                }
                            });

                            google.maps.event.addListener(marker, 'click', function() {
                                $selected_playground = $('#playground-' + letter);

                                $('.playground-list li').removeClass('highlight');
                                $selected_playground.addClass('highlight');

                                $.smoothScroll({ scrollTarget: '#playground-' + letter });
                            })

                            markers.push(marker);
                        }
                    }
                });
            } else {
                if (!user_zoomed && !user_panned) {
                    if (zoom == RESULTS_DEFAULT_ZOOM) {
                        zoom = 11;

                        if (IS_MOBILE) {
                            $search_results_map_loading_text.text('Searching farther away...').show();
                            $search_results_map.css('opacity', '0.25');
                        } else {
                            $map_loading.text('Searching farther away...').show();
                        }

                        search();

                        return false;
                    } else if (zoom == 11) {
                        zoom = 8;

                        if (IS_MOBILE) {
                            $search_results_map_loading_text.text('Searching far away...').show();
                            $search_results_map.css('opacity', '0.25');
                        } else {
                            $map_loading.text('Searching far away...').show();
                        }

                        $zoom_out.attr('disabled', 'disabled');
                        search();

                        return false;
                    } else {
                        not_found = true;
                    }
                } else {
                    not_found = true;
                }
            }

            if (latitude) {
                $search_results_map_wrapper.show();
                $results_address.show();

                if (IS_MOBILE) {
                    var search_map_width = RESULTS_MAP_WIDTH;
                    var search_map_height = RESULTS_MAP_HEIGHT;

                    $search_results_map.on('load', function() {
                        $search_results_map_loading_text.text('Searching...').hide();
                        $search_results_map.css('opacity', '1.0');
                        $search_results_map.off('load');
                    });

                    if (markers.length == 0) {
                        $search_results_map.attr('src', 'http://api.tiles.mapbox.com/v3/' + BASE_LAYER + '/' + longitude + ',' + latitude + ',' + zoom + '/' + search_map_width + 'x' + search_map_height + '.png');
                    } else {
                        $search_results_map.attr('src', 'http://api.tiles.mapbox.com/v3/' + BASE_LAYER + '/' + markers.join(',') + '/' + longitude + ',' + latitude + ',' + zoom + '/' + search_map_width + 'x' + search_map_height + '.png');
                    }
                } else {
                    google.maps.event.trigger(google_desktop_map, 'resize');
                    google_desktop_map.setCenter(latlng);
                    google_desktop_map.setZoom(zoom);
                }
            }

            if (not_found) {
                $search_results_not_found.show();
                $search_results.hide();
                $search_help_prompt.hide();
            } else {
                $search_results.show();
                $search_help_prompt.show();
            }
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

    var state = $.bbq.getState();

    // If we're changing state to exactly where we already are
    // (e.g. because somebody clicked search twice) then don't
    // adjust browser state but force the callback
    if (state['address'] == $search_address.val() &&
        state['latitude'] == $search_latitude.val() &&
        state['longitude'] == $search_longitude.val() &&
        state['zoom'] == zoom.toString() &&
        state['nearby'] == nearby.toString()) {
           hashchange_callback();
    } else {
        $.bbq.pushState({
            'address': $search_address.val(),
            'latitude': $search_latitude.val(),
            'longitude': $search_longitude.val(),
            'zoom': zoom,
            'nearby': nearby
        });
    }
}

function reset_zoom() {
    /*
     * Reset zoom level to default.
     */
    zoom = RESULTS_DEFAULT_ZOOM;
    $zoom_in.removeAttr('disabled');
    $zoom_out.removeAttr('disabled');

    user_zoomed = false;
    user_panned = false;
}

function desktop_map_moveend() {
    var latlng = google_desktop_map.getCenter();
    var current = new google.maps.LatLng($search_latitude.val(), $search_longitude.val());
    zoom = google_desktop_map.getZoom();

    if (!coordinatesApproxEqual(latlng, current, 1000)) {
        $search_latitude.val(latlng.lat());
        $search_longitude.val(latlng.lng());

        user_panned = true;

        navigate();
    }
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
        $did_you_mean_wrapper.hide();
        $search_help_prompt.hide();
        $no_geocode.hide();

        if (!($search_latitude.val() == latitude && $search_longitude.val() == longitude)) {
            if (!user_panned) {
                $search_results_map_wrapper.hide();
                $map_loading.text('Searching...').show();
            }

            user_panned = false;
        } else {
            $results_loading.show();
        }

        $search_latitude.val(latitude);
        $search_longitude.val(longitude);

        if (!nearby) {
            $results_address.text('Accessible Playgrounds Near ' + $search_address.val());
        } else {
            $results_address.text('Accessible Playgrounds Near You');
        }

        search();
    } else if (address) {
        $search_form.submit();
    }
}

function config_map_affix() {
    /*
     * Use Bootstrap affix to anchor slippy map to the top of the page
     * as the user scrolls down a long list of results (e.g., NYC)
     */
    var mc_pos = $('#main-content').position();

    $search_results_wrapper.attr('data-spy', 'affix');
    $search_results_wrapper.attr('data-offset-top', mc_pos.top + 35);

    $('<style type="text/css"> #search-results-wrapper.affix { top: 0; right: ' + mc_pos.left + 'px; margin-right: -8px; width: ' + RESULTS_MAP_WIDTH + 'px; } </style>').appendTo('head');
}

function parse_geocode_results(results, status) {
    $map_loading.hide();
    if (status == google.maps.GeocoderStatus.OK && results[0]['partial_match'] !== true) {
        if (results.length == 1) {
            // If there's one result, render it.
            var result = results[0];
            var latlng = result['geometry']['location'];

            var display_name = result['formatted_address'].replace(', USA', '');
            $search_latitude.val(latlng.lat());
            $search_longitude.val(latlng.lng());
            $search_address.val(display_name);

            $results_address.html('Accessible Playgrounds Near ' + display_name);
            $no_geocode.hide();
            $map_loading.text('Searching...').show();

            navigate(false);
        }
        else {
            // If there are many results,
            // show the did-you-mean path.
            $did_you_mean.empty();
            $no_geocode.hide();
            _.each(results, function(result) {
                result['formatted_address'] = result['formatted_address'].replace(', USA', '');
                var context = $.extend(APP_CONFIG, result);
                var html = JST.did_you_mean_item(context);

                $did_you_mean.append(html);
            });
            $did_you_mean_wrapper.show();
        }
    }
    else {
        $did_you_mean.append('<li>No results</li>');
        $no_geocode.show();
    }
}

function initialize_google_map() {
    var mapOptions = {
        center: new google.maps.LatLng(-34.397, 150.644),
        mapTypeControl: false,
        overviewMapControl: false,
        panControl: false,
        rotateControl: false,
        scaleControl: false,
        scrollwheel: false,
        streetViewControl: false,
        zoomControl: false,
        zoom: 8
    };
    google_desktop_map = new google.maps.Map($('#google-map')[0],
        mapOptions);

    var debounced_moveend = _.debounce(desktop_map_moveend, 200);

    google.maps.event.addListener(google_desktop_map, 'center_changed', debounced_moveend);
    google.maps.event.addListener(google_desktop_map, 'zoom_changed', debounced_moveend);
}


$(function() {
    $search_form = $('#search');
    $search_address = $('#search input[name="address"]');
    $search_again = $('#search-again');
    $search_divider = $search_form.find('h6.divider');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_results_wrapper = $('#search-results-wrapper');
    $search_results = $('#search-results');
    $search_results_ul = $search_results.find('ul');
    $search_results_map_wrapper = $('#search-results-map-wrapper');
    $search_results_map_desktop = $('#search-results-map-desktop');
    $search_results_map = $('#search-results-map');
    $search_results_map_loading_text = $('#search-results-map-loading-text');
    $search_results_not_found = $('#search-results-not-found');
    $zoom_in = $('#zoom-in');
    $zoom_out = $('#zoom-out');
    $did_you_mean_wrapper = $('#search-help');
    $did_you_mean = $('#search-help ul');
    $search_help_prompt = $('#search-help-prompt');
    $search_help_message = $('#search-help-message');
    $results_address = $('#results-address');
    $no_geocode = $('#no-geocode');
    $map_loading = $('#map-loading');
    $results_loading = $('#results-loading');
    $playground_meta_hdr = $('#main-content').find('.about').find('h5.meta');
    $playground_meta_items = $('#main-content').find('.about').find('ul.meta');
    $create_link = $('.create');
    $alerts = $('.alerts');

    PAGE_WIDTH = $(window).width();
    CONTENT_WIDTH = $('#main-content').width();
    SEARCH_WIDTH = $('#main-content').find('.span6:eq(1)').width();
    RESULTS_MAP_WIDTH = SEARCH_WIDTH;
    RESULTS_MAP_HEIGHT = SEARCH_WIDTH;


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
        $results_address.html('Accessible Playgrounds Near ' + display_name);

        $did_you_mean_wrapper.hide();

        $map_loading.text('Searching...').show();
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
        $search_results_not_found.hide();
        $search_results_map_wrapper.hide();
        $results_address.hide();
        $no_geocode.hide();

        reset_zoom();

        var address = $search_address.val();

        if (address) {
            $map_loading.text('Searching...').show();

            if (geocode_xhr) {
                geocode_xhr.cancel();
            }

            geocoder = new google.maps.Geocoder();
            geocoder.geocode({
                'address': address,
                'region': 'us'
            }, parse_geocode_results);

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
        initialize_google_map();
    } else {
        $search_results_map_wrapper.css({ height: RESULTS_MAP_HEIGHT + 'px' });
    }

    if (PAGE_WIDTH > 767 && !IS_MOBILE) {
        config_map_affix();
    }

    // Check to see if we've got a message to show.
    if (get_parameter_by_name('action') !== null){
        // We'll name the message div after the URL param.
        $('#' + get_parameter_by_name('action')).toggleClass('hide').show();
    }

    $(window).bind('hashchange', hashchange_callback);
    $(window).trigger('hashchange');
});
