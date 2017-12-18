
import json
from yolo.box import draw_boxes
from yolo import YOLO
import cv2
from yolo.network import YoloNetwork

def predict(image_path, weights_path, config_path="config.json"):

    with open(config_path) as config_buffer:    
        config = json.load(config_buffer)

    ###############################
    #   Make the model 
    ###############################
    yolo_network = YoloNetwork(config['model']['architecture'],
                               config['model']['input_size'],
                               len(config['model']['labels']),
                               max_box_per_image=10)

    yolo = YOLO(network             = yolo_network,
                labels              = config['model']['labels'], 
                max_box_per_image   = config['model']['max_box_per_image'],
                anchors             = config['model']['anchors'])



    ###############################
    #   Load trained weights
    ###############################    

    print(weights_path)
    yolo.load_weights(weights_path)

    ###############################
    #   Predict bounding boxes 
    ###############################
    image = cv2.imread(image_path)
    boxes = yolo.predict(image)
    image = draw_boxes(image, boxes, config['model']['labels'])

    print(len(boxes), 'boxes are found')

    cv2.imwrite(image_path[:-4] + '_detected' + image_path[-4:], image)
