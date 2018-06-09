$(document).ready(function() {
    $('#dataset_list').DataTable({
        paging: false,
        order: [[ 3, "desc" ]]
    });
} );

$(".add-tag-btn").click(function(){
    var tag_name = prompt("Tag name:");
    var dataset_id = this.id.substring(7);
    if (tag_name !== null)
    {
        $.post( "/tag/add", {dataset_id: dataset_id, tag_name: tag_name}, function( data ) {
          location.reload();
        });
    }
});

$(".unqueue-btn").click(function(){
    var unqueue_id = this.id.split('_')[1];
    $.post( "/unqueue/" + unqueue_id, function( data ) {
        var elem = document.getElementById("sample_queue_" + unqueue_id);
        return elem.parentNode.removeChild(elem);
    });
});

$(".rm-tag-btn").click(function(){
    var dsid = this.id.split('_');
    var dataset_id = dsid[1];
    var tag_name = dsid.slice(2).join('_');
    if (confirm("Remove tag?"))
    {
        $.post( "/tag/remove", {dataset_id: dataset_id, tag_name: tag_name}, function( data ) {
          location.reload();
        });
    }
});
