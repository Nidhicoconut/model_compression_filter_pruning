# model_compression_filter_pruning
This repository contains the implementation of structured pruning techniques applied to CNN architectures (ResNet10 and VGG-11), trained on CIFAR-10 and CIFAR-100 datasets.

This repository contains 8 files corresponding to training and pruning the models

resnet10_setup_cifar10.py – Trains ResNet10 model from scratch on CIFAR-10.
resnet10_setup_cifar100.py – Trains ResNet10 model from scratch on CIFAR-100.
resnet10_cifar10_prune.py – Applies structured filter pruning (L1-norm based) to ResNet10 on CIFAR-10.
resnet10_cifar100_prune.py – Applies structured filter pruning to ResNet10 on CIFAR-100.

vgg_11_scratch_setup_cifar10.py – Trains VGG-11 model from scratch on CIFAR-10.
vgg_11_scratch_setup_cifar100.py – Trains VGG-11 model from scratch on CIFAR-100.
vgg11_scratch_cifar10_prune.py – Performs pruning on VGG-11 trained on CIFAR-10.
vgg11_scratch_cifar100_prune.py – Performs pruning on VGG-11 trained on CIFAR-100.

Steps to implement the project
 1. Setup Environment
 2. Setup Model (resnet10_setup_cifar10.py, resnet10_setup_cifar100.py, vgg_11_scratch_setup_cifar10.py, vgg_11_scratch_setup_cifar100.py)
 3. Prune the Model (resnet10_cifar10_prune.py, resnet10_cifar100_prune.py, vgg11_scratch_cifar10_prune.py, vgg11_scratch_cifar100_prune.py)
