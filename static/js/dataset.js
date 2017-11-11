$(document).ready(function() {
    $('#sample_list').DataTable({
        paging: false,
        order: [[ 0, "asc" ]]
    });
} );

$("#upload_image").change(function(){
         document.getElementById("upload_image_form").submit();
 });

var del_dataset = function(datasete_name){
    if (confirm('Really delete dataset ' + datasete_name + '?'))
    {
        document.getElementById('del_dataset').submit();
    }
}