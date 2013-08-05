var $slideshow = null;
var $slide_back = null;
var $slide_counter = null;
var $slide_next = null;
var $slide_wrapper = null;
var $slides = null;

var slide_current = 0;
var slide_total = null;
var slide_width = null;


function slideshow_init() {
    /* 
     * Create a slideshow out of the items in #slideshow
     */
    slide_total = $slides.length;
    slide_width = $slideshow.width();
    
    $slides.each(function() {
        $(this).css('width', slide_width + 'px');
    }).show();
    $slide_wrapper.css('width', slide_width * slide_total + 'px');
    
    // init buttons
    $slide_back.on('click', go_to_prev_slide);
    $slide_next.on('click', go_to_next_slide);
    
    move_slide(0);
}


// slideshow back/next buttons
function go_to_next_slide() {
    var s = slide_current + 1;
    if (s > (slide_total - 1)) {
        s = 0;
    }
    move_slide(s);
}
function go_to_prev_slide() {
    var s = slide_current - 1;
    if (s < 0) {
        s = slide_total - 1;
    }
    move_slide(s);
}
function move_slide(s) {
    $.smoothScroll({
        direction: 'left',
        scrollElement: $slideshow,
        scrollTarget: '#slide-' + s
    });
    $slide_counter.html('<span>' + (s + 1) + '</span> of <span>' + slide_total + '</span>');
    slide_current = s;
}


$(function() {
    $slideshow = $('#slideshow');
    $slide_back = $('#btn-back');
    $slide_counter = $('#playground-feature-primer').find('nav').find('.counter');
    $slide_next = $('#btn-next');
    $slide_wrapper = $slideshow.find('.slide-wrapper');
    $slides = $slideshow.find('.slide');

    // set up slideshow
    slideshow_init();
});
