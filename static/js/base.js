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

Array.prototype.pushUnique = function (it){
    if(-1 === this.indexOf(it)) { this.push(it); }
};

var getURLParam = function(name) {
    var urlPars = decodeURIComponent(window.location.search.substring(1)).split('&');
    for (var i = 0; i < urlPars.length; ++i) {
        var nameVal = urlPars[i].split('=');
        if (nameVal[0] === name) {
            return nameVal[1];
        }
    }
};


// Init cookie-based dataset list to be added to user if he registers/logs in afterwards
var user_datasets = Cookies.getJSON('datasets');
if (user_datasets === undefined) {
    user_datasets = [];
}

$("#upload_image").change(function(){
         document.getElementById("upload_image_form").submit();
 });
