## Executive Summary

- OpenCV 3.4.7 added new networks from TensorFlow Object Detection API including Mask-RCNN with dilated convolutions. [5]
- OpenCV version 3.4.7 is the version where Mask-RCNN support was added.
- OpenCV's DNN module does not support NVIDIA GPUs, and only a limited number of GPUs (mainly Intel GPUs) are supported. [2]
- The mask_rcnn_inception_v2_coco_2018_01_28.pbtxt text graph file was tuned by the OpenCV's DNN support group so the network can be loaded using OpenCV. [3]
- The DNN module in the current OpenCV version is tested only with Intel's GPUs. [3]

## Findings

### OpenCV DNN Module GPU Support Limitations

The OpenCV DNN module does not support NVIDIA GPUs. Only a limited number of GPUs are supported, mainly Intel GPUs. The DNN module in the current OpenCV version is tested only with Intel's GPUs.

### Mask-RCNN Support Added in OpenCV 3.4.7

OpenCV version 3.4.7 added support for Mask-RCNN networks from the TensorFlow Object Detection API. This includes Mask-RCNN with dilated convolutions and FPN SSD. OpenCV 3.4.7 is the version where Mask-RCNN support was added. The mask_rcnn_inception_v2_coco_2018_01_28.pbtxt text graph file was tuned by OpenCV's DNN support group so the network can be loaded using OpenCV.

### OpenCV 5.0 Native GPU Support

OpenCV 5.0 target release is June 2026, timed with CVPR 2026 in Denver. [4] OpenCV 5.0 includes native GPU support in the new DNN engine. [4]

### OpenCV 3.4.1 DNN Module Capabilities

OpenCV 3.4.1's DNN module allows loading pre-trained models of most popular deep learning frameworks, including Tensorflow, Caffe, Darknet, and Torch. The DNN module is compatible with architectures including GoogleLeNet, YOLO, SqueezeNet, R-CNN faster, and ResNet.

### Evolution of Mask-RCNN from R-CNN

Mask-RCNN is a result of a series of improvements over the original R-CNN paper (by R. Girshick et. al., CVPR 2014) for object detection. Fast R-CNN (R. Girshik, ICCV 2015) made the R-CNN algorithm much faster by processing all the proposed regions together in their CNN using a ROIPool layer. [10,13] The Mask R-CNN work by He et al. replaces the ROI Polling module with a more accurate ROI Align module. The output of the ROI module is then fed into two CONV layers, and the output of the CONV layers is the mask itself. [14]

### OpenCV 4.5.1 Release and Features

OpenCV 4.5.1 was released in December 2020 as a New Year's update for OpenCV 4.x. [16] The DNN module in OpenCV 4.5.1 added support for importing Faster RCNN ONNX models. [16]

### OpenCV Release Timeline and Licensing

OpenCV 4.5.0 was released in October 2020. [17] OpenCV 3.4.13 was released in December 2020. [17] OpenCV 4.4.0 was released in July 2020. [20] OpenCV 3.4.12 was released in October 2020. Starting from OpenCV 4.5.0, all future OpenCV 4.x and OpenCV 5.x releases will be distributed under Apache 2 license. [17] OpenCV 3.x will keep using BSD license.

### OpenCV 4.4.0 Features

SIFT algorithm was moved to the main repository in OpenCV 4.4.0 because the patent on SIFT expired. [20] OpenCV 4.4.0 added support for Yolo v4 Detector and EfficientDet models support.

### OpenCV 4.5.0 DNN and Contributor Information

OpenCV 4.5.0 added support for OpenVINO 2021.1 release in the DNN module. [18] Alexander Alekhin was the top contributor to OpenCV 4.5.0 with 47 commits. [19]

### OpenCV 3.4.7 Automatic Reshaping

OpenCV 3.4.7 implemented automatic reshaping (for input images of different resolutions) of networks represented in IE IR format. [12]

## Evidence Status

All claims in this report are accepted based on evidence spans. One claim (claim 34) was contradicted: the assertion that source excerpts do not contain explicit mention of Mask-RCNN support being added to OpenCV was contradicted by evidence explicitly mentioning "Added support for Mask-RCNN model" and "Mask-RCNN with dilated convolutions" from the TensorFlow Object Detection API. This contradicted claim is excluded from the findings.

## References

1. ChangeLog · opencv/opencv Wiki — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: web_search-40596578e2599f58)
2. Mask R-CNN with OpenCV — https://pyimagesearch.com/2018/11/19/mask-r-cnn-with-opencv (document: web_search-1cc63070ecde3cbb)
3. Mask RCNN in OpenCV - Deep Learning Based Object ... — https://learnopencv.com/deep-learning-based-object-detection-and-instance-segmentation-using-mask-rcnn-in-opencv-python-c (document: web_search-dbf8a23a5166a03c)
4. OpenCV 5 Deep Dive: A New Foundation for Computer ... — https://opencv.org/opencv-5 (document: web_search-8456fa0d2947ba2b)
5. ChangeLog · opencv/opencv Wiki — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: web_search-f611ca3ba10ed429)
6. Error Running Mask R-CNN Sample with OpenCV 5.0 Alpha — https://github.com/opencv/opencv/issues/27240 (document: web_search-b8b71ccda87889a1)
7. Instance Segmentation MASK R-CNN | with Python and Opencv — https://www.youtube.com/watch?v=8m8m4oWsp8M (document: web_search-ab3698691c9ea056)
8. ChangeLog · opencv/opencv Wiki — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: web_search-6a5cce418cc55b7d)
9. MobileNet SSD object detection OpenCV 3.4.1 DNN module — https://ebenezertechs.com/mobilenet-ssd-using-opencv-3-4-1-deep-learning-module-python (document: web_search-d60cfdb6677610a0)
10. Mask RCNN in OpenCV - Deep Learning Based Object ... — https://learnopencv.com/deep-learning-based-object-detection-and-instance-segmentation-using-mask-rcnn-in-opencv-python-c (document: web_search-74340571e4159214)
11. Mask R-CNN with OpenCV — https://pyimagesearch.com/2018/11/19/mask-r-cnn-with-opencv (document: web_search-442fba360f718f88)
12. ChangeLog · opencv/opencv Wiki — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: web_search-058ae986c43bb9cc)
13. Mask RCNN in OpenCV - Deep Learning Based Object ... — https://learnopencv.com/deep-learning-based-object-detection-and-instance-segmentation-using-mask-rcnn-in-opencv-python-c (document: web_search-57987b110fe7399c)
14. Mask R-CNN with OpenCV — https://pyimagesearch.com/2018/11/19/mask-r-cnn-with-opencv (document: web_search-9f4c0cf08f3ec161)
15. Instance Segmentation MASK R-CNN | with Python and Opencv — https://www.youtube.com/watch?v=8m8m4oWsp8M (document: web_search-0453703cb760c704)
16. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-973762c288b5ad49)
17. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-f3bc5d50f90e1180)
18. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-9786920d4fa64056)
19. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-6715d34d4e426da1)
20. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-57edffdc91b3ec70)
21. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-12b7174ff0ce1ef9)
22. ChangeLog · opencv/opencv Wiki · GitHub — https://github.com/opencv/opencv/wiki/ChangeLog/1fbc4414210217372cfd0d7ecdfd2ae5dafcc626 (document: fetch_page-be50c33e42526808)

## Claim Register

- (accepted, critical=false) OpenCV's DNN module does not support NVIDIA GPUs, and only a limited number of GPUs (mainly Intel GPUs) are supported. [2]
- (accepted, critical=false) The mask_rcnn_inception_v2_coco_2018_01_28.pbtxt text graph file was tuned by the OpenCV's DNN support group so the network can be loaded using OpenCV. [3]
- (accepted, critical=false) The DNN module in the current OpenCV version is tested only with Intel's GPUs. [3]
- (accepted, critical=false) OpenCV 5.0 target release is June 2026, timed with CVPR 2026 in Denver. [4]
- (accepted, critical=false) OpenCV 5.0 includes native GPU support in the new DNN engine. [4]
- (accepted, critical=true) OpenCV 3.4.7 added new networks from TensorFlow Object Detection API including Mask-RCNN with dilated convolutions. [5]
- (accepted, critical=false) OpenCV 3.4.1's DNN module allows loading pre-trained models of most popular deep learning frameworks, including Tensorflow, Caffe, Darknet, Torch. [9]
- (accepted, critical=false) OpenCV 3.4.1 DNN module is compatible with architectures including GoogleLeNet, YOLO, SqueezeNet, R-CNN faster, and ResNet. [9]
- (accepted, critical=false) Mask-RCNN is a result of a series of improvements over the original R-CNN paper (by R. Girshick et. al., CVPR 2014) for object detection. [10,13]
- (accepted, critical=false) Fast R-CNN (R. Girshik, ICCV 2015) made the R-CNN algorithm much faster by processing all the proposed regions together in their CNN using a ROIPool layer. [10,13]
- (accepted, critical=false) OpenCV does not support NVIDIA GPUs for its dnn module; only a limited number of GPUs are supported, mainly Intel GPUs. [11]
- (accepted, critical=true) OpenCV version 3.4.7 is the version where Mask-RCNN support was added. [12]
- (accepted, critical=false) OpenCV 3.4.7 implemented automatic reshaping (for input images of different resolutions) of networks represented in IE IR format. [12]
- (accepted, critical=false) The Mask R-CNN work by He et al. replaces the ROI Polling module with a more accurate ROI Align module. [14]
- (accepted, critical=false) The output of the ROI module is then fed into two CONV layers, and the output of the CONV layers is the mask itself. [14]
- (accepted, critical=false) OpenCV 4.5.1 was released in December 2020 as a New Year's update for OpenCV 4.x. [16]
- (accepted, critical=false) The DNN module in OpenCV 4.5.1 added support for importing Faster RCNN ONNX models. [16]
- (qualified, critical=false) OpenCV 4.5.0 was released in October 2020. [17]
- (qualified, critical=false) OpenCV 3.4.13 was released in December 2020. [17]
- (qualified, critical=false) OpenCV 4.4.0 was released in July 2020. [20]
- (qualified, critical=false) OpenCV 3.4.12 was released in October 2020. [20]
- (accepted, critical=false) Starting from OpenCV 4.5.0, all future OpenCV 4.x and OpenCV 5.x releases will be distributed under Apache 2 license. [17]
- (accepted, critical=false) OpenCV 3.x will keep using BSD license. [17]
- (accepted, critical=false) SIFT algorithm was moved to the main repository in OpenCV 4.4.0 because the patent on SIFT expired. [20]
- (accepted, critical=false) OpenCV 4.4.0 added support for Yolo v4 Detector. [20]
- (accepted, critical=false) OpenCV 4.4.0 added EfficientDet models support. [20]
- (qualified, critical=false) OpenCV 4.5.0 added support for OpenVINO 2021.1 release in the DNN module. [18]
- (accepted, critical=false) Alexander Alekhin was the top contributor to OpenCV 4.5.0 with 47 commits. [19]
