import torch
torch.load("denoising/models/net_rgb.pth", map_location="cpu", weights_only=False)
print("✅ File loads fine!")
