#! /usr/bin/env python
# Todo : sample driver file => ipython notebook description
import argparse
import json
import cv2
from yolo.frontend import create_yolo
from yolo.backend.utils.box import draw_boxes
import os
import yolo

TEST_SAMPLE_DIR = os.path.join(yolo.PROJECT_ROOT, "tests", "dataset")


DEFAULT_CONFIG_FILE = os.path.join(TEST_SAMPLE_DIR, "pred_config.json")
DEFAULT_INPUT_IMAGE = os.path.join(TEST_SAMPLE_DIR, "raccoon.jpg")

argparser = argparse.ArgumentParser(
    description='Train and validate YOLO_v2 model on any dataset')

argparser.add_argument(
    '-c',
    '--conf',
    default=DEFAULT_CONFIG_FILE,
    help='path to configuration file')

argparser.add_argument(
    '-i',
    '--input',
    default=DEFAULT_INPUT_IMAGE,
    help='path to an image or an video (mp4 format)')

if __name__ == '__main__':
    # 1. extract arguments
    args = argparser.parse_args()
    with open(args.conf) as config_buffer:
        config = json.loads(config_buffer.read())

    # 2. read image
    image = cv2.imread(args.input)

    # Todo : pretrained feature message
    # 3. create yolo instance & predict
    yolo = create_yolo(config['architecture'],
                       config['labels'],
                       config['input_size'],
                       config['max_box_per_image'],
                       config['anchors'],
                       os.path.join(TEST_SAMPLE_DIR, "mobilenet_raccoon.h5"),
                       None)
    boxes, probs = yolo.predict(image)

    # 4. save detection result
    output_path = args.input[:-4] + '_detected' + args.input[-4:]
    image = draw_boxes(image, boxes, probs, config['labels'])
    cv2.imwrite(output_path, image)
    print("{}-boxes are detected. {} saved.".format(len(boxes), output_path))

    
