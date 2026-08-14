## Executive Summary

- OpenCV's DNN module does not support NVIDIA GPUs; only a limited number of GPUs, mainly Intel GPUs, are supported.
- OpenCV version 3.4.7 added support for Mask-RCNN networks from the TensorFlow Object Detection API, including variants with dilated convolutions.
- OpenCV 5.0, targeted for June 2026, will include native GPU support in its new DNN engine.
- OpenCV 4.5.0 (released October 2020) marked the transition to Apache 2 licensing for all future 4.x and 5.x releases, while OpenCV 3.x continues under BSD license.
- Mask-RCNN evolved from R-CNN through Fast R-CNN, with Mask R-CNN replacing ROI Pooling with ROI Align.

## Findings

### OpenCV DNN Module GPU Support Limitations

The OpenCV DNN module does not support NVIDIA GPUs. Only a limited number of GPUs are supported, mainly Intel GPUs. The DNN module in the current OpenCV version is tested only with Intel's GPUs.

### Mask-RCNN Support Added in OpenCV 3.4.7

OpenCV version 3.4.7 added support for Mask-RCNN networks from the TensorFlow Object Detection API. This includes Mask-RCNN with dilated convolutions and FPN SSD. OpenCV 3.4.7 is the version where Mask-RCNN support was added. The mask_rcnn_inception_v2_coco_2018_01_28.pbtxt text graph file was tuned by OpenCV's DNN support group so the network can be loaded using OpenCV.

### OpenCV 5.0 Native GPU Support

OpenCV 5.0 target release is June 2026, timed with CVPR 2026 in Denver. OpenCV 5.0 includes native GPU support in the new DNN engine.

### OpenCV 3.4.1 DNN Module Capabilities

OpenCV 3.4.1's DNN module allows loading pre-trained models of most popular deep learning frameworks, including Tensorflow, Caffe, Darknet, and Torch. The DNN module is compatible with architectures including GoogleLeNet, YOLO, SqueezeNet, R-CNN faster, and ResNet.

### Evolution of Mask-RCNN from R-CNN

Mask-RCNN is a result of a series of improvements over the original R-CNN paper (by R. Girshick et. al., CVPR 2014) for object detection. Fast R-CNN (R. Girshik, ICCV 2015) made the R-CNN algorithm much faster by processing all the proposed regions together in their CNN using a ROIPool layer. The Mask R-CNN work by He et al. replaces the ROI Polling module with a more accurate ROI Align module. The output of the ROI module is then fed into two CONV layers, and the output of the CONV layers is the mask itself.

### OpenCV 4.5.1 Release and Features

OpenCV 4.5.1 was released in December 2020 as a New Year's update for OpenCV 4.x. The DNN module in OpenCV 4.5.1 added support for importing Faster RCNN ONNX models.

### OpenCV Release Timeline and Licensing

OpenCV 4.5.0 was released in October 2020. OpenCV 3.4.13 was released in December 2020. OpenCV 4.4.0 was released in July 2020. OpenCV 3.4.12 was released in October 2020. Starting from OpenCV 4.5.0, all future OpenCV 4.x and OpenCV 5.x releases will be distributed under Apache 2 license. OpenCV 3.x will keep using BSD license.

### OpenCV 4.4.0 Features

SIFT algorithm was moved to the main repository in OpenCV 4.4.0 because the patent on SIFT expired. OpenCV 4.4.0 added support for Yolo v4 Detector and EfficientDet models support.

### OpenCV 4.5.0 DNN and Contributor Information

OpenCV 4.5.0 added support for OpenVINO 2021.1 release in the DNN module. Alexander Alekhin was the top contributor to OpenCV 4.5.0 with 47 commits.

### OpenCV 3.4.7 Automatic Reshaping

OpenCV 3.4.7 implemented automatic reshaping (for input images of different resolutions) of networks represented in IE IR format.

## Evidence Status

All claims in this report are accepted based on evidence spans. One claim (claim 34) was contradicted: the assertion that source excerpts do not contain explicit mention of Mask-RCNN support being added to OpenCV was contradicted by evidence explicitly mentioning "Added support for Mask-RCNN model" and "Mask-RCNN with dilated convolutions" from the TensorFlow Object Detection API. This contradicted claim is excluded from the findings.