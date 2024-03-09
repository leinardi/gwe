import os
import sys
from pynvml import *

nvmlInit()
sys.stderr.write('ready\n')
while True:
    for line in sys.stdin:
        splits = line.split(' ')
        handle = nvmlDeviceGetHandleByIndex(int(splits[0]))
        if splits[1] == 'pl':
            try:
                nvmlDeviceSetPowerManagementLimit(handle, int(splits[2]))
                sys.stderr.write(str(NVML_SUCCESS) + '\n')
            except NVMLError as err:
                sys.stderr.write(str(err.value) + '\n')
        elif splits[1] == 'pm':
            try:
                nvmlDeviceSetPersistenceMode(handle, int(splits[2]))
                sys.stderr.write(str(NVML_SUCCESS) + '\n')
            except NVMLError as err:
                sys.stderr.write(str(err.value) + '\n')
        elif splits[1] == 'gpu':
            try:
                nvmlDeviceSetGpcClkVfOffset(handle, int(splits[2]))
                sys.stderr.write(str(NVML_SUCCESS) + '\n')
            except NVMLError as err:
                sys.stderr.write(str(err.value) + '\n')
        elif splits[1] == 'mem':
            try:
                nvmlDeviceSetMemClkVfOffset(handle, int(splits[2]))
                sys.stderr.write(str(NVML_SUCCESS) + '\n')
            except NVMLError as err:
                sys.stderr.write(str(err.value) + '\n')
        elif splits[1] == 'quit':
            nvmlShutdown()
            sys.stderr.write(str(NVML_SUCCESS) + '\n')
            exit()
