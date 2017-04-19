/* Annotation */

var annotation_margin = 32;
var display_radius = 32;
var svg = d3.select("#annotation_svg");

var annotations = [];
var last_stoma_id = 0;
var update_display;

Array.prototype.removeIf = function(callback) {
    var i = this.length;
    while (i--) {
        if (callback(this[i], i)) {
            this.splice(i, 1);
        }
    }
};

var stomaClick = function() {
  var id = parseInt(this.getAttribute("id").substr(5));
  annotations.removeIf(function(stoma, index) { return stoma.id == id; });
  d3.select(this).remove();
  d3.event.stopPropagation();
};

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