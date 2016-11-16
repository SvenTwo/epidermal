Epidermal images test project

Train and test an AlexNet on annotated stomata images. All experimental; nothing organized yet. Scripts to be used in
the following order:

    paths.py            - Modify this to include local paths
    mkepinet.py         - Generate the model definition structure (requires serrecaffe. Not neeed if you use an existing
                          model definition)
    archive2dataset.py  - Take sample epidermal images and CSV files with coordinates to create a stomata versus non-
                          stomata dataset to train the network on

    convert_model_to_fcn.py - Convert the trained classification model into a fully convolutional model which gives
                              stomata estimates per pixel
    apply_fcn.py        - Apply a trained FCN to generate stomata predictions on a set of test images
