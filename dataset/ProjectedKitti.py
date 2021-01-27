import os
import numpy as np
import torch
from torch.utils.data import Dataset
from .laserscan import LaserScan, SemLaserScan
import torch.nn.functional as F
from torchvision import transforms
import yaml
import cv2
import glob



class SemanticProjectedKitti(Dataset):

  def __init__(self, data_dir, data_stats, val_split_ratio, is_train_data=True):
    # save deats
    self.data_dir = data_dir
    self.data_stats = data_stats
    # get number of classes (can't be len(self.learning_map) because there
    # are multiple repeated entries, so the number that matters is how many
    # there are for the xentropy)
    # sanity checks
    # make sure directory exists
    if os.path.isdir(self.data_dir):
      print("Sequences folder exists! Using sequences from %s" % self.data_dir)
    else:
      raise ValueError("Sequences folder doesn't exist! Exiting...")
    
    self.scan_file_names = glob.glob(data_dir + '/*')
    self.scan_file_names.sort()
    total_samples = len(self.scan_file_names)
    train_indcs = list(range(total_samples))[int(val_split_ratio*total_samples):]
    val_indcs = list(range(total_samples))[:int(val_split_ratio*total_samples)]
    self.scan_file_names = [self.scan_file_names[i] for i in (train_indcs if is_train_data else val_indcs)]

  def __getitem__(self, index):
    # get item in tensor shape
    scan_file = self.scan_file_names[index]
    proj = np.load(scan_file)
      # map unused classes to used classes (also for projection)
      # scan.sem_label = self.map(scan.sem_label, self.learning_map)
      # scan.proj_sem_label = self.map(scan.proj_sem_label, self.learning_map)
      # proj_labels = proj_labels * proj_mask 
   
    Min = np.array(self.data_stats['img_min'])[:, None, None]
    Max = np.array(self.data_stats['img_max'])[:, None, None]
    proj[:5] = (proj[:5] - Min)/(Max - Min)
    proj[:5] = (proj[:5] - 0.5)/0.5

    proj = np.repeat(proj, 4 , axis= 1)
    proj_mask = torch.from_numpy(proj[5:6]).clone()
    proj_xyz = torch.from_numpy(proj[:3]).clone() * proj_mask
    proj_range = torch.from_numpy(proj[3:4]).clone() * proj_mask
    proj_remission = torch.from_numpy(proj[4:5]).clone() * proj_mask
    
    return proj_xyz , proj_remission, proj_range, proj_mask

  def __len__(self):
    return len(self.scan_file_names)

  @staticmethod
  def map(label, mapdict):
    # put label from original values to xentropy
    # or vice-versa, depending on dictionary values
    # make learning map a lookup table
    maxkey = 0
    for key, data in mapdict.items():
      if isinstance(data, list):
        nel = len(data)
      else:
        nel = 1
      if key > maxkey:
        maxkey = key
    # +100 hack making lut bigger just in case there are unknown labels
    if nel > 1:
      lut = np.zeros((maxkey + 100, nel), dtype=np.int32)
    else:
      lut = np.zeros((maxkey + 100), dtype=np.int32)
    for key, data in mapdict.items():
      try:
        lut[key] = data
      except IndexError:
        print("Wrong key ", key)
    # do the mapping
    return lut[label]


class Kitti_Loader():
  # standard conv, BN, relu
  def __init__(self,
               data_dir,              # directory for data
               batch_size,        # batch size for train and val
               data_stats,
               val_slpit_ratio,
               workers=4,           # threads to load data
               gt=True,           # get gt?
               shuffle_train=True):  # shuffle training set?
    super(Kitti_Loader, self).__init__()

    

    # number of classes that matters is the one for xentropy
    train_dataset = SemanticProjectedKitti(data_dir, data_stats, val_slpit_ratio)
    val_dataset = SemanticProjectedKitti(data_dir, data_stats, val_slpit_ratio, False)
    
    self.trainloader = torch.utils.data.DataLoader(train_dataset,
                                                   batch_size=batch_size,
                                                   shuffle=shuffle_train,
                                                   num_workers=workers,
                                                   drop_last=True)
    assert len(self.trainloader) > 0

    self.validloader = torch.utils.data.DataLoader(val_dataset,
                                                   batch_size=batch_size,
                                                   shuffle=False,
                                                   num_workers=workers,
                                                   drop_last=True)
    assert len(self.validloader) > 0









