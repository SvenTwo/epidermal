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

var setDatasetThresholdProb = function(prob_ds_id, previous_prob)
{
    var new_prob_str = prompt("Enter new threshold probability (default 0.982) between 0.5 and 1.0", previous_prob);
    new_prob = parseFloat(new_prob_str);
    if (new_prob_str === null) {
        // cancelled
        return;
    }
    if(isNaN(new_prob) || new_prob < 0.5 || new_prob > 1.0)
    {
        alert("Invalid probability value.");
    }
    else
    {
        window.location = "/dataset/" + prob_ds_id + "/set_threshold/" + new_prob;
    }
};


// In case we need to remember this dataset
if (getURLParam('new') === 'true') {
    user_datasets.pushUnique(dataset_id);
    Cookies.set('datasets', user_datasets);
}