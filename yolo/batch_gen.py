
import numpy as np
np.random.seed(1337)
import yolo.augment as augment
from keras.utils import Sequence
from yolo.box import BoundBox, bbox_iou, to_centroid, to_normalize


class GeneratorConfig(object):
    
    def __init__(self,
                 input_size,
                 grid_size,
                 labels,
                 batch_size,
                 max_box_per_image,
                 anchors):
        self.input_size = input_size
        self.grid_size = grid_size
        self.nb_box = int(len(anchors)/2)
        self.labels = labels
        self.anchors = anchors
        self.batch_size = batch_size
        self.max_box_per_image = max_box_per_image
        self.n_classes = len(self.labels)


class LabelBatchGenerator(object):
    
    def __init__(self, input_size, grid_size, nb_box, n_classes, max_box_per_image, anchors):
        self.input_size = input_size
        self.grid_size = grid_size
        self.nb_box = nb_box
        self.n_classes = n_classes
        self.anchors = self._create_anchor_boxes(anchors)
        self.max_box_per_image = max_box_per_image

    def _create_anchor_boxes(self, anchors):
        n_anchor_boxes = int(len(anchors)/2)
        return [BoundBox(0, 0, anchors[2*i], anchors[2*i+1]) 
                for i in range(n_anchor_boxes)]

    def _get_anchor_idx(self, box):
        _, _, center_w, center_h = box
        
        # find the anchor that best predicts this box
        best_anchor = -1
        max_iou     = -1
        
        shifted_box = BoundBox(0, 
                               0, 
                               center_w, 
                               center_h)
        
        for i in range(len(self.anchors)):
            anchor = self.anchors[i]
            iou    = bbox_iou(shifted_box, anchor)
            
            if max_iou < iou:
                best_anchor = i
                max_iou     = iou
        return best_anchor
    
    def _generate_y(self, best_anchor, obj_indx, box):
        y = np.zeros((self.grid_size,  self.grid_size, self.nb_box, 4+1+self.n_classes))
        grid_x, grid_y, _, _ = box.astype(int)
        y[grid_y, grid_x, best_anchor, 0:4] = box
        y[grid_y, grid_x, best_anchor, 4  ] = 1.
        y[grid_y, grid_x, best_anchor, 5+obj_indx] = 1
        return y
    
    def generate(self, boxes, labels):
        """
        
        labels : list of integers
        """
        
        # construct output from object's x, y, w, h
        true_box_index = 0
        
        y = np.zeros((self.grid_size,
                      self.grid_size,
                      self.nb_box,
                      4+1+self.n_classes))
        b_ = np.zeros((1,1,1,
                       self.max_box_per_image,
                       4))
        
        centroid_boxes = to_centroid(boxes)
        norm_boxes = to_normalize(centroid_boxes, self.input_size, self.grid_size)
        
        # loop over objects in one image
        for norm_box, label in zip(norm_boxes, labels):
            best_anchor = self._get_anchor_idx(norm_box)

            # assign ground truth x, y, w, h, confidence and class probs to y_batch
            y += self._generate_y(best_anchor, label, norm_box)
            
            # assign the true box to b_batch
            b_[0, 0, 0, true_box_index] = norm_box
            
            true_box_index += 1
            true_box_index = true_box_index % self.max_box_per_image
        return y, b_



class BatchGenerator(Sequence):
    def __init__(self, annotations, 
                       config, 
                       jitter=True, 
                       norm=None):
        """
        # Args
            annotations : Annotations instance
        
            images : list of dictionary including following keys
                "filename"  : str
                "width"     : int
                "height"    : int
                "object"    : list of dictionary
                    'name' : str
                    'xmin' : int
                    'ymin' : int
                    'xmax' : int
                    'ymax' : int
        """
        self.annotations = annotations
        self.batch_size = config.batch_size
        
        #def __init__(self, input_size, grid_size, nb_box, n_classes, anchors):
        self._label_generator = LabelBatchGenerator(config.input_size,
                                                    config.grid_size,
                                                    config.nb_box,
                                                    config.n_classes,
                                                    config.max_box_per_image,
                                                    config.anchors)

        self.config = config
        self.jitter  = jitter
        if norm is None:
            self.norm = lambda x: x
        else:
            self.norm = norm
        self.counter = 0

    def __len__(self):
        return len(self.annotations._components)

    def __getitem__(self, idx):
        """
        # Args
            idx : int
                batch index
        """
        # batch_size = self._ann_handler.get_batch_size(idx)
        instance_count = 0

        x_batch = np.zeros((self.batch_size, self.config.input_size, self.config.input_size, 3))                         # input images
        b_batch = np.zeros((self.batch_size, 1     , 1     , 1    ,  self.config.max_box_per_image, 4))   # list of self.config['TRUE_self.config['BOX']_BUFFER'] GT boxes
        y_batch = np.zeros((self.batch_size, self.config.grid_size,  self.config.grid_size, self.config.nb_box, 4+1+self.config.n_classes))                # desired network output

        for i in range(self.batch_size):
            # 1. get input file & its annotation
            fname = self.annotations.fname(self.batch_size*idx + i)
            boxes = self.annotations.boxes(self.batch_size*idx + i)
            labels = self.annotations.code_labels(self.batch_size*idx + i)
            
            # 2. read image in fixed size
            img, boxes = augment.imread(fname,
                                        boxes,
                                        self.config.input_size,
                                        self.config.input_size,
                                        self.jitter)
            
            # 3. generate x_batch
            x_batch[instance_count] = self.norm(img)
            
            # 4. generate y_batch, b_batch
            y_batch[instance_count], b_batch[instance_count] = self._label_generator.generate(boxes, labels)
            instance_count += 1

        self.counter += 1
        return [x_batch, b_batch], y_batch

    def on_epoch_end(self):
        self.annotations.shuffle()
        self.counter = 0


import pytest
@pytest.fixture(scope='function')
def setup():
    import json
    from yolo.annotation import parse_annotation
    with open("config.json") as config_buffer:    
        config = json.loads(config_buffer.read())
        
    generator_config = GeneratorConfig(config["model"]["input_size"],
                                       int(config["model"]["input_size"]/32),
                                       labels = config["model"]["labels"],
                                       batch_size = 8,
                                       max_box_per_image = config["model"]["max_box_per_image"],
                                       anchors = config["model"]["anchors"])

    train_annotations, train_labels = parse_annotation(config['train']['train_annot_folder'], 
                                                       config['train']['train_image_folder'], 
                                                       config['model']['labels'])
    return train_annotations, generator_config

@pytest.fixture(scope='function')
def expected():
    x_batch_gt = np.load("x_batch_gt.npy")
    b_batch_gt = np.load("b_batch_gt.npy")
    y_batch_gt = np.load("y_batch_gt.npy")
    return x_batch_gt, b_batch_gt, y_batch_gt

def test_generate_batch(setup, expected):
    train_annotations, config = setup
    x_batch_gt, b_batch_gt, y_batch_gt = expected

    batch_gen = BatchGenerator(train_annotations, config, False)
    
    # (8, 416, 416, 3) (8, 1, 1, 1, 10, 4) (8, 13, 13, 5, 6)
    (x_batch, b_batch), y_batch = batch_gen[0]
    
    assert np.array_equal(x_batch, x_batch_gt) == True 
    assert np.array_equal(b_batch, b_batch_gt) == True 
    assert np.array_equal(y_batch, y_batch_gt) == True 


if __name__ == '__main__':
    pytest.main([__file__, "-v", "-s"])

        
