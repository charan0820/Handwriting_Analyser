import torch
import torch.nn as nn

from .cnn import CNNFeatureExtractor
from .sequence_model import SequenceModel


class CRNN(nn.Module):
    def __init__(self, num_classes: int, cnn_channels: list[int] = None, hidden_size: int = 256):
        super().__init__()
        self.cnn = CNNFeatureExtractor(cnn_channels)
        self.rnn = SequenceModel(self.cnn.channels[-1], hidden_size)
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.cnn(x).squeeze(2).permute(2, 0, 1)  # (T,B,C)
        return self.fc(self.rnn(feat))  # (T,B,num_classes)


def build_crnn(num_classes: int, cnn_channels: list[int] = None, hidden_size: int = 256) -> nn.Module:
    return CRNN(num_classes, cnn_channels, hidden_size)


if __name__ == "__main__":
    m = build_crnn(68)
    out = m(torch.randn(4, 1, 64, 256))
    assert out.shape == (64, 4, 68)
    print("OK", out.shape)
