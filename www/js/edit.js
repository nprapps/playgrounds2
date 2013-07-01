var $edit_map = null;

$(function() {
   $edit_map = $('#edit-map');
   $edit_map.width(300);
   $edit_map.height(500);
   edit_map = L.mapbox.map('edit-map', 'examples.map-y7l23tes')
      .setView([37.9, -77], 5);
});
