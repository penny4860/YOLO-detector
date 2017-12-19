# -*- coding: utf-8 -*-
import json
import os
import numpy as np
from yolo.annotation import parse_annotation
from yolo import YOLO
from yolo.backend import create_feature_extractor
from yolo.network import YoloNetwork


def train(conf):

    config_path = conf

    with open(config_path) as config_buffer:    
        config = json.loads(config_buffer.read())

    ###############################
    #   Parse the annotations 
    ###############################

    # parse annotations of the training set
    train_imgs, train_labels = parse_annotation(config['train']['train_annot_folder'], 
                                                config['train']['train_image_folder'], 
                                                config['model']['labels'])

    # parse annotations of the validation set, if any, otherwise split the training set
    if os.path.exists(config['valid']['valid_annot_folder']):
        valid_imgs, valid_labels = parse_annotation(config['valid']['valid_annot_folder'], 
                                                    config['valid']['valid_image_folder'], 
                                                    config['model']['labels'])
    else:
        train_valid_split = int(0.8*len(train_imgs))
        np.random.shuffle(train_imgs)

        valid_imgs = train_imgs[train_valid_split:]
        train_imgs = train_imgs[:train_valid_split]

    
    overlap_labels = set(config['model']['labels']).intersection(set(train_labels.keys()))

    print('Seen labels:\t', train_labels)
    print('Given labels:\t', config['model']['labels'])
    print('Overlap labels:\t', overlap_labels)    

    if len(overlap_labels) < len(config['model']['labels']):
        print('Some labels have no images! Please revise the list of labels in the config.json file!')
        return
        
    ###############################
    #   Construct the model 
    ###############################

    yolo_network = YoloNetwork(config['model']['architecture'],
                               config['model']['input_size'],
                               len(config['model']['labels']),
                               max_box_per_image=10)
    
    from yolo.loss import YoloLoss
    yolo_loss = YoloLoss(yolo_network.grid_size,
                         config['model']['anchors'],
                         yolo_network.nb_box,
                         len(config['model']['labels']),
                         yolo_network.true_boxes)

    yolo = YOLO(network             = yolo_network,
                loss                = yolo_loss,
                labels              = config['model']['labels'], 
                anchors             = config['model']['anchors'])

    ###############################
    #   Load the pretrained weights (if any) 
    ###############################    

    if os.path.exists(config['train']['pretrained_weights']):
        print("Loading pre-trained weights in", config['train']['pretrained_weights'])
        yolo.load_weights(config['train']['pretrained_weights'])

    ###############################
    #   Start the training process 
    ###############################

    yolo.train(train_imgs         = train_imgs,
               valid_imgs         = valid_imgs,
               train_times        = config['train']['train_times'],
               valid_times        = config['valid']['valid_times'],
               nb_epoch           = config['train']['nb_epoch'], 
               learning_rate      = config['train']['learning_rate'], 
               batch_size         = config['train']['batch_size'],
               warmup_epochs      = config['train']['warmup_epochs'],
               saved_weights_name = config['train']['saved_weights_name'],
               debug              = config['train']['debug'])
