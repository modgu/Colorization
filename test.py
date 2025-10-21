import torch
from networks.models import Colorizer

device = "cpu"
colorizer = Colorizer()
colorizer.generator.load_state_dict(torch.load("networks/generator.zip", map_location=device))
torch.save(colorizer.generator.state_dict(), "networks/generator.pth")
print("✅ Converted generator.zip → generator.pth")
