#coding=utf-8
import cv2
import math
import numpy as np
from net.net import BuildModel
from net.util import gen_input, NMS
import keras.backend as K
import tensorflow as tf


class Detector(object):

    def __init__(self):
        self.stride = 2  # search stride
        self.models = {}  # model path
        self.scale_factor = 0.709  # image search scale
        self.min_size = 12
        self.min_box = 24
        self.threshold = [0.7, 0.9, 0.9]
        self.input_size = (640, 480, 3)
        self.init_net()

    def init_net(self):
        self.models["pnet"], self.pgraph, self.psess = BuildModel("pnet", pretrain_path="./models/pnet.h5")
        self.models["rnet"], self.rgraph, self.rsess = BuildModel("rnet", pretrain_path="./models/rnet.h5")
        self.models["onet"], self.ograph, self.osess = BuildModel("onet", pretrain_path="./models/onet.h5")
        # self.save_as_pb()

    def predict(self, cv_img, stage="onet"):
        with self.pgraph.as_default():
            with self.psess.as_default():
                candis = self.run_pnet(self.models["pnet"], cv_img)
                if stage == "pnet":
                    return candis
        with self.rgraph.as_default():
            with self.rsess.as_default():
                rnet_candis = self.run_rnet(self.models["rnet"], cv_img, candis)
                if stage == "rnet":
                    return rnet_candis
        with self.ograph.as_default():
            with self.osess.as_default():
                onet_candis = self.run_onet(self.models["onet"], cv_img, rnet_candis)
                return onet_candis

    def save_as_pb(self, outdir="./models/"):
        from tensorflow.python.framework.graph_util import convert_variables_to_constants
        model_name = "pnet.pb"
        for key in self.models:
            model = self.models[key]
            model_name = key + ".pb"
            if key == "pnet":
                graph, sess = self.pgraph, self.psess
            elif key == "rnet":
                graph, sess = self.rgraph, self.rsess
            elif key == "onet":
                graph, sess = self.ograph, self.osess
            with graph.as_default():
                with sess.as_default():
                    out_names = [v.name.split(":")[0] for v in model.output]
                    node_names = out_names
                    frozon_graph = convert_variables_to_constants(sess, graph.as_graph_def(), node_names)
                    tf.train.write_graph(frozon_graph, outdir, model_name, as_text=False)

    def run_pnet(self, models, image, size=12):
        height, width = image.shape[:2]
        pnet_candis = []
        scale = 1
        while height * scale >= self.min_size and width * scale >= self.min_size:
            h, w = int(height * scale), int(width * scale)
            scale_img = cv2.resize(image, (w, h))
            probs, reg_box = models.predict(np.array([scale_img]), batch_size=1)
            probs = probs[:, :, :, 1]
            boxes = self.selection(image, probs[0], reg_box[0], scale, size)
            nms_boxes = NMS(boxes, 0.5, "union")
            pnet_candis += nms_boxes
            scale *= self.scale_factor
        pnet_candis = NMS(pnet_candis, 0.7, "union")
        pnet_candis = self.box_regression(image, pnet_candis)
        return pnet_candis

    def box_regression(self, image, candis, square_padding=True):
        # 0:4-> box  5:9 box-reg 9->prob
        cp_img = image.copy()
        result = []
        for elm in candis:
            #rx1, ry1, rx2, ry2, reg_x1, reg_y1, reg_x2, reg_y2, prob = elm
            loc, prob = np.array(elm[:8]), elm[-1]
            loc = loc.reshape((-1, 2))  #  4 * 2
            loc[:2] += loc[2:4]
            rx1, ry1, rx2, ry2 = loc[:2].reshape((-1,))
            if square_padding:
                w, h = loc[1] - loc[0]
                square_size = max(w, h)
                rx1 = rx1 + square_size / 2 - w / 2
                rx2 = rx2 + square_size / 2 - w / 2
                ry1 = ry1 + square_size / 2 - h / 2
                ry2 = ry2 + square_size / 2 - h / 2
                if min(ry2 - ry1, rx2 - rx1) < self.min_box:
                    continue


            result.append([rx1, ry1, rx2, ry2, 0, 0, 0, 0, prob])
        return result

    def selection(self, image, probs, boxes_reg, scale, size=12):
        candis = []
        h, w = probs.shape
        for c in range(w):
            for r in range(h):
                if probs[r][c] > self.threshold[0]:
                    reg_box = reg_x1, reg_y1, reg_x2, reg_y2 = boxes_reg[r][c]
                    rx1 = int((c * self.stride) / scale)
                    ry1 = int((r * self.stride) / scale)
                    rx2 = int((c * self.stride + size) / scale)
                    ry2 = int((r * self.stride + size) / scale)
                    reg_x1 = int((reg_x1 * size) / scale)
                    reg_y1 = int((reg_y1 * size) / scale)
                    reg_x2 = int((reg_x2 * size) / scale)
                    reg_y2 = int((reg_y2 * size) / scale)

                    candis.append([rx1, ry1, rx2, ry2, reg_x1, reg_y1, reg_x2, reg_y2, probs[r][c]])
        return candis

    def run_rnet(self, models, image, candis, size=24):
        if not candis:
            return []
        feedbox = []
        for elm in candis:
            rx1, ry1, rx2, ry2 = list(map(int, elm[:4]))
            feedbox.append(cv2.resize(image[max(ry1, 0):ry2+1, max(rx1, 0):rx2+1,:], (24, 24)))
        rnet_candis = models.predict(np.array(feedbox))
        mask = rnet_candis[0][:, 1] > self.threshold[1]
        mask_prob = rnet_candis[0][:, 1]
        reg_box = rnet_candis[1]
        rnet_candis = []
        for idx, elm in enumerate(candis):
            if mask_prob[idx] < self.threshold[1]:
                 continue
            rx1, ry1, rx2, ry2 = map(int, elm[:4])
            reg_rx1 = int(size * reg_box[idx][0])
            reg_ry1 = int(size * reg_box[idx][1])
            reg_rx2 = int(size * reg_box[idx][2])
            reg_ry2 = int(size * reg_box[idx][3])
            rnet_candis.append([rx1, ry1, rx2, ry2, reg_rx1, reg_ry1, reg_rx2, reg_ry2, mask_prob[idx]])
        rnet_candis = NMS(rnet_candis, 0.4, "min")
        rnet_candis = self.box_regression(image, rnet_candis)
        return rnet_candis

    def run_onet(self, models, image, candis, size=48):
        if not candis:
            return []
        feedbox = []
        for elm in candis:
            rx1, ry1, rx2, ry2 = list(map(int, elm[:4]))
            feedbox.append(cv2.resize(image[max(ry1, 0):ry2+1, max(rx1, 0):rx2+1,:], (48, 48)))

        onet_candis = models.predict(np.array(feedbox))
        mask_prob = onet_candis[0][:, 1]
        candis = np.array(candis)
        reg_box = onet_candis[1]
        key_points = onet_candis[2]
        onet_candis = []
        for idx, elm in enumerate(candis):
            if mask_prob[idx] < self.threshold[2]:
                 continue
            rx1, ry1, rx2, ry2 = map(int, elm[:4])
            reg_rx1 = int(size * reg_box[idx][0])
            reg_ry1 = int(size * reg_box[idx][1])
            reg_rx2 = int(size * reg_box[idx][2])
            reg_ry2 = int(size * reg_box[idx][3])

            onet_candis.append([rx1, ry1, rx2, ry2, reg_rx1, reg_ry1, reg_rx2, reg_ry2, mask_prob[idx]])
        onet_candis = NMS(onet_candis, 0.4, "min")
        for elm in onet_candis:
            rx1, ry1, rx2, ry2 = elm[:4]
            cv2.rectangle(image, (rx1, ry1), (rx2, ry2), (0, 255, 0), 2)
        # cv2.imwrite("test_pri.jpg", image)
        return onet_candis
