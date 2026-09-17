import torch
import torch.nn as nn


class CNNFeatureExtractor(nn.Module):
    """Collapses (B, 1, 64, 256) -> (B, C, 1, T=64)."""

    def __init__(self, channels: list[int] = None):
        super().__init__()
        channels = channels or [32, 64, 128, 128, 256]
        self.channels = channels
        self.stub_conv = nn.Conv2d(1, channels[-1], kernel_size=1)  # TODO Day 4: real conv stack

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.stub_conv(x)
        feat = nn.functional.adaptive_avg_pool2d(feat, (1, 64))
        return feat  # (B, C, 1, T)
