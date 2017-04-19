/* Annotation */

var update_display;

var annotation_margin = 32;
var display_radius = 32;
var svg = d3.select("#annotation_svg");

var last_stoma_id = 0;
var annotations = saved_annotations.map(function(stoma){
    return { x: stoma.x, y: stoma.y, id: ++last_stoma_id };
});

// Click on annotation: Remove annotation
var stomaClick = function() {
  // Find annotation to remove
  var id = parseInt(this.getAttribute("id").substr(5));
  // Remove from array
  annotations.removeIf(function(stoma, index) { return stoma.id == id; });
  // Remove from display
  d3.select(this).remove();
  // Don't process click event on container
  d3.event.stopPropagation();
};


// Update positions / add missing stomata elements to be drawn
update_display = function() {
  var circles = svg.selectAll("circle");
  circles.data(annotations).enter().append("circle")
    .attr("cx", function(d) { return d.x; })
    .attr("cy", function(d) { return d.y; })
    .attr("r", display_radius)
    .attr("class", "stoma")
    .attr("id", function(d) { return "stoma" + d.id; })
    .on("mousedown", stomaClick);
};


// Main SVG clicks: Add new stomata
svg.on("mousedown", function() {
    // On click: Add new annotation
    var coords = d3.mouse(this);
    var new_annotation = {
      x: coords[0],
      y: coords[1],
      id: ++last_stoma_id
    };
    annotations.push(new_annotation);
    update_display();
});

// Initial update of loaded annotations
update_display();


// Save annotation
$(document).ready(function(){
    $("#save_annotations_form").submit( function(eventObj) {
        var send_annotations = annotations.map(function(stoma) {
                return { x: stoma.x, y: stoma.y }
            });
        $('#form_annotations').attr('value', JSON.stringify(send_annotations));
        $('#form_margin').attr('value', ""+annotation_margin);
        return true;
    });
});