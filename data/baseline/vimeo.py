import os
from os import path
import glob
import random

from data import common
from data.meta_learner import preprocessing
from data import random_kernel_generator as rkg

import numpy as np
import math, imageio
import data.util as util

import torch
import torch.utils.data as data


class Vimeo(data.Dataset):
    """Vimeo trainset class
    """
    def __init__(self, opt, train=True, **kwargs):
        super().__init__()
        self.data_root = opt['datasets']['train']['data_root']
        self.data_root = path.join(self.data_root, 'vimeo_septuplet')
        if train:
            meta = "F:/vimeo_septuplet/sep_trainlist.txt"
        else:
            meta = "F:/vimeo_septuplet/sep_testlist.txt"

        with open(meta, 'r') as f:
            self.img_list = sorted(f.read().splitlines())
        self.opt = opt
        self.scale = opt['scale']
        self.nframes = opt['datasets']['train']['N_frames']
        self.train = train
        
        sigma_x = float(opt['sigma_x'])
        sigma_y = float(opt['sigma_y'])
        theta = float(opt['theta'])
        kernel_size = int(opt['kernel_size'])
        gen_kwargs = preprocessing.set_kernel_params(sigma_x=sigma_x, sigma_y=sigma_y, theta=theta)
        self.kernel_gen = rkg.Degradation(kernel_size, self.scale, **gen_kwargs)

    def __getitem__(self, idx):
        name_hr = path.join(self.data_root, 'sequences', self.img_list[idx])
        names_hr = sorted(glob.glob(path.join(name_hr, '*.png')))
        names = [path.splitext(path.basename(f))[0] for f in names_hr]
        names = [path.join(self.img_list[idx], name) for name in names]
        
        seq_hr = [imageio.imread(f) for f in names_hr]
        seq_hr = np.stack(seq_hr, axis=-1)
        start_frame = random.randint(0, 7-self.nframes)
        seq_hr = seq_hr[..., start_frame:start_frame+self.nframes]
        seq_hr = preprocessing.np2tensor(seq_hr)
        
        if self.train:
            seq_hr = preprocessing.crop_border(seq_hr, border=[4, 4])
            seq_hr = preprocessing.common_crop(seq_hr, patch_size=self.opt['datasets']['train']['patch_size']*4)
            seq_hr = util.augment(seq_hr, self.opt['use_flip'], self.opt['use_rot'])
            

        # include random noise for each frame
        
        kwargs = preprocessing.set_kernel_params()
        kernel_gen = rkg.Degradation(self.opt['datasets']['train']['kernel_size'], self.scale, **kwargs)
        seq_lr, kernel = kernel_gen.apply(seq_hr)
        seq_lr = seq_lr.mul(255).clamp(0, 255).round().div(255)
        
        return {'LQs': seq_lr, 'GT': seq_hr}

    def __len__(self):
        return len(self.img_list)
