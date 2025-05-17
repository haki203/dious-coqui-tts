import torch

print("CUDA available:", torch.cuda.is_available())
print("cuDNN available:", torch.backends.cudnn.is_available())
print("GPU name:", torch.cuda.get_device_name(0))
