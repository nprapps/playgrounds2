var CONTENT_WIDTH;
var GEOLOCATE = Modernizr.geolocation;

var $search_form = null;
var $search_latitude = null;
var $search_longitude = null;
var $search_address = null;
var $geolocate_button = null;
var $search_divider = null;
var $playground_meta_hdr = null;
var $playground_meta_items = null;

$(function() {
    $search_form = $('#search');
    $search_address = $('#search input[name="address"]');
    $search_latitude = $('#search input[name="latitude"]');
    $search_longitude = $('#search input[name="longitude"]');
    $geolocate_button = $('#geolocate');
    $search_divider = $search_form.find('h6.divider');
    $playground_meta_hdr = $('#main-content').find('.about').find('h5.meta');
    $playground_meta_items = $('#main-content').find('.about').find('ul.meta');
    $alerts = $('.alerts');

    CONTENT_WIDTH = $('#main-content').width();
    RESULTS_MAP_WIDTH = CONTENT_WIDTH;
    RESULTS_MAP_HEIGHT = CONTENT_WIDTH;

    /* THE THANK YOU MESSAGE BLOCK */

    // This is a function from the internet for parsing the URL location.
    // Returns undefined if the key doesn't exist; returns the value if it does.
    function getURLParameter(name) {
        return decodeURI(
            (RegExp(name + '=' + '(.+?)(&|$)').exec(location.search)||[null])[1]
        );
    }

    // Fetches the key from the URL. This could easily be undefined or null.
    var action = getURLParameter('action');

    // If the URL parameter doesn't exist or is blank, don't do anything.
    // If it does exist, pass to write_message.
    // This block handles looking up the key from the URL and the message from the copy text.
    if ((action !== "undefined") && (action !== null)) {
        // Look up the message in the copy text.
        var message = COPYTEXT[action];
        // Only if the message exists should writeMessage() get called.
        if ((message !== "undefined") && (message !== null)) {
            // Use mustache for insertions
            _.templateSettings = {
                interpolate: /\{\{(.+?)\}\}/g
            };
            // Colorize the alert
            var klass = 'alert-info';
            // Add a close button; timeOut instead?
            var button = '<button type="button" class="close" data-dismiss="alert">&times;</button>';
            // Template up the alert
            var messageTemplate = _.template(
                '<div class="alert {{ klass }}">{{ button }}{{ text }}</div>'
            );
            // Pass it to the div
            $alerts.append(messageTemplate({
                klass: klass, button: button, text: message
            }));
        }
    }

    $geolocate_button.click(function() {
        navigator.geolocation.getCurrentPosition(function(position) {
            window.location.href = 'search.html#latitude=' + position.coords.latitude + '&longitude=' + position.coords.longitude + '&nearby=true'; 
        });
    });

    $search_form.submit(function() {
        window.location.href = 'search.html#address=' + encodeURIComponent($search_address.val()); 

        return false;
    });

    if (GEOLOCATE) {
        $geolocate_button.show();
        $search_divider.show();
    }
});
