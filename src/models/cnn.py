import torch
import torch.nn as nn


class CNNFeatureExtractor(nn.Module):
    """(B,1,64,256) -> (B,256,1,64). See crnn.py docstring for the downsampling plan."""

    def __init__(self, channels: list[int] = None):
        super().__init__()
        c = channels or [32, 64, 128, 128, 256]
        self.channels = c
        self.net = nn.Sequential(
            nn.Conv2d(1, c[0], 3, padding=1), nn.ReLU(), nn.MaxPool2d(2, 2),        # H32,W128
            nn.Conv2d(c[0], c[1], 3, padding=1), nn.ReLU(), nn.MaxPool2d(2, 2),     # H16,W64
            nn.Conv2d(c[1], c[2], 3, padding=1), nn.ReLU(),
            nn.MaxPool2d((2, 1)),                                                    # H8,W64
            nn.Conv2d(c[2], c[3], 3, padding=1), nn.BatchNorm2d(c[3]), nn.ReLU(),
            nn.MaxPool2d((2, 1)),                                                    # H4,W64
            nn.Conv2d(c[3], c[4], 3, padding=1), nn.BatchNorm2d(c[4]), nn.ReLU(),
            nn.MaxPool2d((2, 1)),                                                    # H2,W64
            nn.Conv2d(c[4], c[4], 2, stride=(2, 1)), nn.ReLU(),                      # H1,W64
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)  # (B,C,1,T)
