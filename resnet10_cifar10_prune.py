# -*- coding: utf-8 -*-
"""Copy of resnet10_cifar10_prune.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1z2uKwtN8bmcLe1-yuIBQT2hgiU01JC3y
"""

import torch
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models
import torch.nn as nn
from torch.utils.data import DataLoader
import torch.nn.functional as F

from google.colab import drive
drive.mount('/content/drive')

transform = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomCrop(32, padding=4),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.4914, 0.4822, 0.4465], std=[0.2470, 0.2435, 0.2616])
])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform)
trainloader = DataLoader(trainset, batch_size=128, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform)
testloader = DataLoader(testset, batch_size=128, shuffle=False, num_workers=2)

class BasicBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return F.relu(out)

class ResNet10(nn.Module):
    def __init__(self, num_classes=10, pruned_channels=None):
        super(ResNet10, self).__init__()
        if pruned_channels is None:
            pruned_channels = {64: 64, 128: 128, 256: 256, 512: 512}

        self.conv1 = nn.Conv2d(3, pruned_channels[64], kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(pruned_channels[64])
        self.layer1 = BasicBlock(pruned_channels[64], pruned_channels[64])
        self.layer2 = BasicBlock(pruned_channels[64], pruned_channels[128], stride=2)
        self.layer3 = BasicBlock(pruned_channels[128], pruned_channels[256], stride=2)
        self.layer4 = BasicBlock(pruned_channels[256], pruned_channels[512], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(pruned_channels[512], num_classes)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.avgpool(out)
        out = torch.flatten(out, 1)
        return self.fc(out)

model = torch.load("/content/drive/MyDrive/resnet10_cifar10_full.pth", map_location=device, weights_only=False)
model.to(device)
model.eval()

torch.save(model.state_dict(), "resnet10_cifar10_weights.pth")

model.eval()
print("Model loaded successfully and ready for inference!")

def evaluate_model(model, dataloader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in dataloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    return 100 * correct / total

accuracy_initial = evaluate_model(model, testloader, device)

print(accuracy_initial)

!pip install thop

import torch
from thop import profile

accuracy_dict = {}
flops_dict = {}
params_dict = {}

accuracy_dict['initial'] = accuracy_initial

with torch.cuda.device(0 if torch.cuda.is_available() else -1):
    flops, params = profile(model, inputs=(torch.randn(1, 3, 32, 32).to(device),))

flops_dict['initial'] = flops
params_dict['initial'] = params

print(f"Accuracy: {accuracy_dict['initial']:.4f}%")
print(f"FLOPs: {flops_dict['initial'] / 1e6:.4f} MFLOPs")
print(f"Params: {params_dict['initial'] / 1e6:.4f} MParams")

def compute_flops(model, input_size=(1, 3, 32, 32)):
    from thop import profile
    dummy_input = torch.randn(input_size)
    flops, _ = profile(model, inputs=(dummy_input,))
    return flops

def compute_params(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

import torch.nn.utils.prune as prune

def prune_resnet10_model(model, prune_ratio):
    pruned_channels = {}

    print("Filter Pruning Details:")

    for name, module in model.named_modules():
        if isinstance(module, nn.Conv2d):
            l1_norms = module.weight.data.abs().sum(dim=(1, 2, 3))
            num_prune = int(module.out_channels * prune_ratio)
            keep_indices = torch.argsort(l1_norms, descending=True)[num_prune:]

            original_filters = module.out_channels
            pruned_filters = len(keep_indices)

            pruned_channels[module.out_channels] = pruned_filters

            print(f"Pruning {name} - {original_filters} filters -> {pruned_filters} filters  ")

    new_model = ResNet10(pruned_channels=pruned_channels)
    return new_model

def finetune_model(model, trainloader, device, epochs=3):
    model.to(device)
    model.train()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    for epoch in range(epochs):
        for images, labels in trainloader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
    return model

prune_ratios = [0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]

accuracy_dict = {}
flops_dict = {}
params_dict = {}

for ratio in prune_ratios:
    print(f"\n=== Pruning ratio: {ratio} ===")

    state_dict = torch.load("resnet10_cifar10_weights.pth")

    filtered_state_dict = {k: v for k, v in state_dict.items() if not ('.total_ops' in k or '.total_params' in k or k in ['total_ops', 'total_params'])}

    base_model = ResNet10()
    base_model.load_state_dict(filtered_state_dict)
    base_model.to(device)
    base_model.eval()


    pruned_model = prune_resnet10_model(base_model, prune_ratio=ratio).to(device)
    pruned_model = finetune_model(pruned_model, trainloader, device, epochs=3)

    acc = evaluate_model(pruned_model, testloader, device)

    with torch.cuda.device(0 if torch.cuda.is_available() else -1):
        flops, params = profile(pruned_model, inputs=(torch.randn(1, 3, 32, 32).to(device),))

    accuracy_dict[ratio] = acc
    flops_dict[ratio] = flops
    params_dict[ratio] = params

    print(f"Accuracy for ratio {ratio}: {acc:.4f}%")
    print(f"FLOPs for ratio {ratio}: {flops / 1e6:.4f} MFLOPs")
    print(f"Params for ratio {ratio}: {params / 1e6:.4f} MParams")

print("\nFinal Results:")
for ratio in accuracy_dict:
    print(f"Pruning Ratio: {ratio}, Accuracy: {accuracy_dict[ratio]:.4f}%")
for ratio in flops_dict:
    print(f"Pruning Ratio: {ratio}, FLOPs: {flops_dict[ratio] / 1e6:.4f} MFLOPs")
for ratio in params_dict:
    print(f"Pruning Ratio: {ratio}, Params: {params_dict[ratio] / 1e6:.4f} MParams")

import pickle
with open('pruning_results_res10cif10.pkl', 'wb') as f:
    pickle.dump({'accuracy_dict': accuracy_dict, 'flops_dict': flops_dict, 'params_dict': params_dict}, f)

print("Data saved successfully!")