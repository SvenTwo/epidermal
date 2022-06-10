# Stomata Counter

Finds and counts stomata in microscopic images of leaves. This is code for developers who intend to build their own web service or train their own models. If you just want to evaluate images, you can use our existing service running at http://www.stomata.science/

## Installation of Dependencies

Download the latest version of the code:

    mkdir ~/epidermal
    git clone https://github.com/SvenTwo/epidermal.git ~/epidermal/
    cd ~/epidermal

The project is python2.7-based using caffe for the CNN processing. First install caffe http://caffe.berkeleyvision.org/installation.html
and remember to also install the python bindings (`make pycaffe` if you compile yourself). For all basic python dependencies (you may want to enter a virtualenv to install all dependencies in usermode if desired first):

```buildoutcfg
for req in $(cat requirements.txt); do pip install $req; done 
```  

pyIMQ for image quality measures is also required and can be found here: https://github.com/danielsnider/PyImageQualityRanking - if pyimq is not installed, the service should run but image quality measures will not be available.

## Command-Line Interface

If you prefer to not use the web service, a script can be used for batch processing locally. It can be used to input a set of images and output CSV file with stomata counts, and optionally create heatmaps of each processed image.

Download the most current pre-trained model weights from here [[Download]](https://drive.google.com/file/d/18qirGnLD3oEpInyp1KAVf9ZsKf_MQkRb/view?usp=sharing) (alexnetftc_iter_5000_fcn.caffemodel and sc_feb2019.prototxt), or the published model weights here [[Download]](https://drive.google.com/open?id=1StStt1aiN8q1rvSnSVY--87CQ8Z4Pf9b) (sc_feb2019.caffemodel and sc_feb2019.prototxt) and unzip the two files. 

The processing command allows tweaking various settings such as the input scale and detection threshold. The interface is:

    python2.7 process_images.py [-h] --weights-filename WEIGHTS_FILENAME
                         --proto-filename PROTO_FILENAME
                         [--gpu-index GPU_INDEX]
                         [--cnn-top-layer-name CNN_TOP_LAYER_NAME]
                         [--scale SCALE]
                         [--heatmap-output-path HEATMAP_OUTPUT_PATH]
                         [--plot-contours] [--plot-no-peaks]
                         [--prob-threshold PROB_THRESHOLD]
                         [--prob-area-threshold PROB_AREA_THRESHOLD]
                         --csv-output-filename CSV_OUTPUT_FILENAME
                         [--output-fields {count,image_filename,imq_entropy,imq_hf_entropy,imq_hf_kurtosis,imq_hf_mean,imq_hf_power,imq_hf_skewness,imq_hf_std,imq_hf_threshfreq,margin,positions,scale} [{count,image_filename,imq_entropy,imq_hf_entropy,imq_hf_kurtosis,imq_hf_mean,imq_hf_power,imq_hf_skewness,imq_hf_std,imq_hf_threshfreq,margin,positions,scale} ...]]
                         [--verbose]
                         image-paths [image-paths ...]
                         
From the downloaded model, pass the .caffemodel as `--weights-filename` and the .prototxt as `--proto-filename`. For example:

`TODO`
 

## Hosting Stomata Counter

The project consists of three different services that communicate via a MongoDb and a locally mounted filesystem:

1. The web service is a python flask-based service that serves the web page, allows uploads and issues processing and training requests via the database.

2. The processing worker is a python-based worker service that listens for images to be processed on the database and processes them as needed. It uses a GPU if available. Multiple processing workers can be run in parallel to allow faster throughput, although that feature hasn't been tested extensively.

3. The training worker is a python-based worker service that listens for training requests issued by the admin interface of the web service. It has to run on a GPU. The training worker is not required to run the service. It would typically run on the same GPU as the processing worker.


### Configuration

All services share a configuration file from the home path of the current user (*~/.epidermal*). To create a file with default values, either run one of the services or just run from the command line:

    python2.7 config.py
   
Following is the meaning of the fields. **Remember to configure an admin password and security cookies before the first start**:

Name | Default value | Meaning
:--- | :--- | :---
debug_flask | False | Set to True to enable debug mode, which outputs useful error messages into the browser when something goes wrong.
db_address | localhost | Hostname for the main image MongoDB connection. If everything is hosted on one machine, this can be a loopback address.
db_port | 27017 | Port of main image MongoDB address.
db_name | epidermal | MongoDB database name.
admin_username | admin | Administrator username.
admin_password | password | Password for admin access. **Configure this before start**  
data_path | ~/epidermal/data | Path where files generated by the service and workers are written.
train_data_path | ~/epidermal/data/train | Intermediate training data path for when model is re-trained.
caffe_path | ~/caffe/build | Path to find caffe executables for model training.
caffe_train_baseweights | ~/epidermal/bvlc_reference_caffenet.caffemodel | Path to find initial weights for model training.
caffe_train_options | --gpu 0 | Additional options passed to caffe training command line.
model_path | ~/epidermal/data/models | Path to store trained model files.
server_path | ~/epidermal/data/server | Path to store trained model files.
server_image_path | ~/epidermal/data/server/images | Path to store trained model files.
server_heatmap_path | ~/epidermal/data/server/heatmaps | Path to store trained model files.
image_extensions | .jpg,.jpeg,.png | Comma-separated list of supported image file extensions.
archive_extensions | .zip | Comma-separated list of supported archive file extensions.
max_image_file_size | 52428800 | Maximum file size for uploaded images (in bytes)
worker_gpu_index | 0 | Index of GPU to use by apply worker, unless specified on command line. Set to -1 for CPU processing.
src_path | ./ | Path to store trained model files.
APP_SECRET_KEY | | Cookie key for user management. **Configure this before start**
APP_SECURITY_REGISTERABLE | True | If users can register on the site.
APP_SECURITY_CHANGEABLE | True | If users can change their password.
APP_SECURITY_PASSWORD_SALT | | Salt for user password storage. **Configure this before start**
APP_DEFAULT_MAIL_SENDER | stomatacounter@gmail.com | E-mails sent from this address.
APP_SECURITY_EMAIL_SENDER | stomatacounter@gmail.com | E-mails sent from this address.
APP_SECURITY_REGISTERABLE | True | Whether users can create accounts.
APP_SECURITY_CONFIRMABLE | False | Whether email confirmation is required on new accounts.
APP_SECURITY_RECOVERABLE | True | Whether users can send their passwords to their registered address.
APP_MAIL_SERVER | smtp.gmail.com | SMTP server to be used for sending mails to users.
APP_MAIL_PORT | 465 | SMTP server port to be used for sending mails to users.
APP_MAIL_USE_SSL | True | Use encryption for user e-mails. 
APP_MAIL_USERNAME | stomatacounter@gmail.com | E-mails sent from this address.
APP_MAIL_PASSWORD | | SMTP mail password to be used for sending emails.
APP_MONGODB_DB | epidermal | Database name for user management MongoDB. 
APP_MONGODB_HOST | localhost | Database host for user management MongoDB. Usually same as db_address.
APP_MONGODB_PORT | 27017 | Database port for user management MongoDB. Usually same as db_port.
plot_path | ~/epidermal/data/plots | Path to store plots of evaluation scripts.
cnn_path | ~/epidermal/data/cnn | Model files.
maintenance_text | | Set to non-empty to replace all pages with a maintenance message.
automatic_deletion_days | 36500 | Number of days after last access after which datasets that have no tags are deleted automatically.
 
 

### Web service
 
The web service is located in *webapp.py*, which can simply be run to serve directly from flask. However, it is recommended to use a more powerful standalone web server to allow multiple processes. The app is available in wsgi.py. To launch e.g. via gunicorn (http://docs.gunicorn.org/en/stable/install.html):

    gunicorn --timeout 1200 --workers 3 --bind 0.0.0.0:8000 wsgi
    
This would launch the service on port 8000. You can then open a browser on http://localhost:8000/ to test if things work. If you want to host publicly, I recommend to forward port 80 to 8000 instead of hosting directly on the low port, so that the app can be run without root privileges.
Annotation and custom model training can be done via the admin interface on the web service.  



### Annotation worker

When images are uploaded, the web service puts worker jobs into a MongoDB. The actual computation is handled by a separate process which can be launched as:

     python2.7 apply_worker.py
     
Note that the apply worker needs to have a model saved in the database (either trained via annotations from the web interface or imported from another service).
     
     
### Train worker

The service can be run without extra training if only inference should be done. If you want to improve the model using annotated images, launch a train worker using:

     python2.7 train_worker.py
     
As with inference, training jobs can be launched via the web interface.
