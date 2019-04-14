# Stomata Counter

Finds and counts stomata in microscopic images of leaves. This is code for developers who intend to build their own web service or train their own models. If you just want to evaluate images, you can use our existing service running at http://www.stomata.science/

## Installation

The project is python2.7-based using caffe for the CNN processing. First install caffe http://caffe.berkeleyvision.org/installation.html
and remember to also install the python bindings (`make pycaffe` if you compile yourself). For all basic python dependencies:

```buildoutcfg
for req in $(cat requirements.txt); do pip install $req; done 
```  

pyIMQ for image quality measures is also required and can be found here: https://github.com/danielsnider/PyImageQualityRanking - if pyimq is not installed, the service should run but image quality measures will not be available.

## Command-Line Interface

If you prefer to not use the web service, a script can be used for batch processing locally. It can be used to input a set of images and output CSV file with stomata counts, and optionally create heatmaps of each processed image.

Download the pre-trained model weights from here [[Download]](https://drive.google.com/open?id=1StStt1aiN8q1rvSnSVY--87CQ8Z4Pf9b) and unzip the two files (sc_feb2019.caffemodel and sc_feb2019.prototxt). 

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
 

## Web service

Annotation and custom model training can be done via the admin interface on the web service. To run the web service:

`TODO`

    paths.py            - Modify this to include local paths
    mkepinet.py         - Generate the model definition structure (requires serrecaffe. Not neeed if you use an existing
                          model definition)
    archive2dataset.py  - Take sample epidermal images and CSV files with coordinates to create a stomata versus non-
                          stomata dataset to train the network on

    convert_model_to_fcn.py - Convert the trained classification model into a fully convolutional model which gives
                              stomata estimates per pixel
    apply_fcn.py        - Apply a trained FCN to generate stomata predictions on a set of test images
    webapp.py           - Flask App serving the stomata ID upload and viewing server
    worker.py           - Worker process that processes unprocessed images from the web app. Should be run while the
                          webapp runs.
