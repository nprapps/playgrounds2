function degToRad(degree) {
    /*
     * Convert degrees to radians.
     */
    return degree * Math.PI / 180;
}

function radToDeg(radian) {
    /*
     * Convert radians to degrees.
     */
    return radian / Math.PI * 180;
}

function get_parameter_by_name(name) {
    name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function formatMapQuestAddress(locale) {
    var quality = locale['geocodeQuality'];
    var street = locale['street'];
    var city = locale['adminArea5'];
    var state = locale['adminArea3'];
    var county = locale['adminArea4'];
    var zip = locale['postalCode'];

    if (quality == 'POINT' || quality == 'ADDRESS' || quality == 'INTERSECTION') {
        return street + ' ' + city + ', ' + state + ' ' +  zip;
    } else if (quality == 'CITY') {
        return city + ', ' + state;
    } else if (quality == 'COUNTY') {
        return county + ' County, ' + state;
    } else if (quality == 'ZIP' || quality == 'ZIP_EXTENDED') {
        return zip + ', ' + state;
    } else if (quality == 'STATE') {
        return state;
    } else {
        return '';
    }
}

function require_us_address(locale) {
    var country = locale['adminArea1'];
    if (country !== 'US') {
        make_alert('Please choose an address within the United States.', 'warning');
    }
}

function prevent_body_scroll(e) {
    if (!$('.scrollable').has($(e.target)).length) {
        e.preventDefault();
    }
}

function make_alert(text, klass){
    // Generate a template.
    var alert_template = _.template('<div class="alert <%= klass %>"><%= text %></div>');

    // Blank the div and add our rendered template.
    $('div.alerts').html('').append(
        alert_template({
            'text': text,
            'klass': klass
        })
    );

    // Make it disappear reasonably quickly after 2 seconds.
    var t = setTimeout(function(){
        $('div.alerts .alert').fadeOut(500, function(){
            $('div.alerts').html('');
        });
    }, 2000);
}

function set_driving_urls(){
    var $directions_wrapper = $('.directions-wrapper');
    var $directions_link = $('#directions-link');
    if (navigator.userAgent.match(/iPhone|iPad|iPod/i)){
        // handle iOS

        var directions_header = $('<h4>Get Driving Directions</h4>');
        var google_maps_link = $('<a class="btn btn-blue"><i class="icon icon-google-plus"></i>Google Maps</a>');

        $directions_link.attr('href', $directions_link.data('ios-map'));
        $directions_link.html('<i class="icon icon-apple"></i> Apple Maps');
        google_maps_link.attr('href', $directions_link.data('ios-gmap'));

        $directions_link.parent().before(directions_header);
        $directions_link.after(google_maps_link);
    }
}

$(function(){
    if (navigator.userAgent.match(/iPhone|iPad|iPod/i)){
        set_driving_urls();
    }
});