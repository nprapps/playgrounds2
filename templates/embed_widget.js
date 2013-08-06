if(window.station == undefined) {
    window.station = '';
}

var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%3Cscript src=\'" + gaJsHost + "google-analytics.com/ga.js\' type=\'text/javascript\'%3E%3C/script%3E"));

try {
	var pageTracker = _gat._getTracker("UA-5828686-3");
	pageTracker._setDomainName("none");
	pageTracker._setAllowLinker(true);
	pageTracker._setCustomVar(1,"Module","accessible_playgrounds",3);
	pageTracker._trackPageview();
} catch(err) {}

/* check for user-defined width */
try {
	if (nprapps_widget_width) {}
} catch (err) {
	nprapps_widget_width = '500';
}

try {
	if (nprapps_widget_height) {}
} catch (err) {
	nprapps_widget_height = '850';
}

document.write(
'<iframe src="{{ S3_BASE_URL }}/widget.html?station=' + window.station + '" width="' + nprapps_widget_width + '" height="' + nprapps_widget_height + '" scrolling="auto" marginheight="0" marginwidth="0" frameborder="0"></iframe>',
'');
