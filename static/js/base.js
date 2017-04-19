/* Common JS functions for epidermal project */

function addDataset(){
    var name = prompt("Dataset name", "untitled");
    if (name != null)
    {
        $('input[name="dataset_name"]').val(name);
        $( "#add_dataset_form" ).submit();
    }
}

Array.prototype.removeIf = function(callback) {
    var i = this.length;
    while (i--) {
        if (callback(this[i], i)) {
            this.splice(i, 1);
        }
    }
};