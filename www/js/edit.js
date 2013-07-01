var $edit_map = null;

$(function() {
   $edit_map = $('#edit-map');
   $edit_map.width('100%');
   $edit_map.height('250');
   map = L.map('edit-map').setView([38.9, -77], 7);
   map_layer = L.mapbox.tileLayer('geraldrich.map-wow338yo', {
       detectRetina: true,
       retinaVersion: 'geraldrich.map-y6mt2diq'
   }).addTo(map);
   grid_layer = L.mapbox.gridLayer('geraldricamples.map-wow338yo').addTo(map);
   map.addControl(L.mapbox.gridControl(grid_layer));
});
