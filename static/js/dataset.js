$(document).ready(function() {
    $('#sample_list').DataTable({
        paging: false,
        order: [[ 0, "asc" ]]
    });
} );

var del_dataset = function(datasete_name){
    if (confirm('Really delete dataset ' + datasete_name + '?'))
    {
        document.getElementById('del_dataset').submit();
    }
};


// In case we need to remember this dataset
if (getURLParam('new') === 'true') {
    user_datasets.pushUnique(dataset_id);
    Cookies.set('datasets', user_datasets);
}