$(document).ready(function() {
    $('#dataset_list').DataTable({
        paging: false,
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
})

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
})
