var LETTERS = 'abcdefghijklmnopqrstuvwxyz';
var DEFAULT_ZOOM = 12;
var RESULTS_MAP_WIDTH = null;
var RESULTS_MAP_HEIGHT = null;

var $map = null;
var $form = null;
var $zip_code = null;
var $results = null;

var zoom = DEFAULT_ZOOM;
var map = null;
var markers = null;

var search_xhr = null;
var geocode_xhr = null;

function search(latitude, longitude) {
    /*
     * Execute a search using current UI state.
     */
    $results.empty();

    console.log(latitude, longitude);

    map.removeLayer(markers);

    if (search_xhr != null) {
        search_xhr.abort();
    }

    search_xhr = $.ajax({
        url: APP_CONFIG.CLOUD_SEARCH_PROXY_BASE_URL + '/cloudsearch/2011-02-01/search?' + $.param(buildCloudSearchParams(latitude, longitude, zoom)),
        dataType: 'jsonp',
        complete: function() {
            search_xhr = null;
        },
        success: function(data) {
            // TODO: hide loading indicator

            var markers = [];

            if (data['hits']['hit'].length > 0) {
                _.each(data['hits']['hit'], function(hit, i) {
                    var context = $.extend(APP_CONFIG, hit);
                    context['letter'] = LETTERS[i];
                    
                    context['features'] = [];
                    
                    // Generate a list of included features
                    for (feature in window.FEATURES) {
                        var key = 'feature_' + feature.replace(/-/g, '_');

                        if (hit['data'][key][0] > 0) {
                            context['features'].push(window.FEATURES[feature]);
                        }
                    }

                    var html = JST.playground_item(context);
                    $results.append(html);

                    if (hit.data.latitude.length > 0) {
                        var lat = cloudSearchToDeg(hit.data.latitude[0]);
                        var lng = cloudSearchToDeg(hit.data.longitude[0]);

                        var marker = L.mapbox.marker.style({
                            'type': 'Feature',
                            'geometry': {},
                            'properties': {
                                'marker-size': 'medium',
                                'marker-symbol': context['letter'],
                                'marker-color': '#ff6633'
                            }
                        }, [lat, lng]);

                        /*marker.letter = context['letter'];

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
                        });*/

                        markers.push(marker);
                    }
                });

                map.setView([latitude, longitude], zoom);

                markers.clearLayers();

                _.each(markers, function(marker) {
                    markers.addLayer(marker);
                });
                
                map.addLayer(markers);

                // TODO: create link
                //$create_link.attr('href', 'create.html?latitude=' + latitude + '&longitude=' + longitude); 
            } else {
                // TODO: no results
                alert('No results!');
            }
        },
        cache: true
    });
}

function on_submit() {
    if ($zip_code.val() == '') {
        return false;
    }

    $results.empty();
    
    var zip_code = $zip_code.val();

    alert(zip_code);

    // TODO: loading indicator

    if (geocode_xhr) {
        geocode_xhr.cancel();
    }

    // TODO: is there a better way to query specifically a zip code
    geocode_xhr = $.ajax({
        'url': 'http://open.mapquestapi.com/nominatim/v1/search.php?format=json&countrycodes=US&json_callback=playgroundCallback&q=' + zip_code,
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
            // TODO: hide loading indicator

            if (data.length === 0) {
                // TODO: If there are no results, show a nice message.
                alert('No results');
            } else if (data.length == 1) {
                // If there's one result, render it.
                var locale = data[0];

                //var display_name = locale['display_name'].replace(', United States of America', '');
                //$search_latitude.val(locale['lat']);
                //$search_longitude.val(locale['lon']);

                search(locale['lat'], locale['lon']);
            } else {
                // TODO: If there are many results show the did-you-mean path.
                alert('Multiple results, using first');
                
                var locale = data[0];
                search(locale['lat'], locale['lon']);
            }
        }
    });

    return false;
}


$(function() {
    $map = $('#map');
    $form = $('form');
    $zip_code = $('#zip-code');
    $results = $('#results');

    $form.submit(on_submit);

    RESULTS_MAP_WIDTH = $map.width();
    RESULTS_MAP_HEIGHT = $map.height();

    map = L.mapbox.map('map', null, {
        zoomControl: false,
        scrollWheelZoom: false
    });

    var tiles = L.mapbox.tileLayer('npr.map-s5q5dags', {
        detectRetina: true,
        retinaVersion: 'npr.map-u1zkdj0e',
    });

    tiles.addTo(map);

    markers = L.layerGroup();
});
