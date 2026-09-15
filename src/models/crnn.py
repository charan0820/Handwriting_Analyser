"""
Day 1 — CRNN architecture skeleton (Member 2)

No training yet. This file exists so Member 1 and Member 3 can import a real
module and check their tensor shapes against it starting Day 2/3, instead of
waiting for the full model on Day 4.

Design target (from config.yaml):
    Input:  (B, 1, 64, 256)   grayscale, H=64, W=256
    Output: (T, B, num_classes)  T = sequence length after CNN downsampling

CNN downsampling plan (height must collapse to 1, width becomes the sequence
length T fed to the BiLSTM):
    Input H=64, W=256
      conv+pool (2,2) -> H=32, W=128
      conv+pool (2,2) -> H=16, W=64
      conv+pool (2,1) -> H=8,  W=64   (stop squashing width so T stays usable)
      conv+pool (2,1) -> H=4,  W=64
      conv+pool (2,1) -> H=2,  W=64
      conv          -> H=1,  W=64    (squeeze height to 1)
    => T = 64 timesteps, feature dim = last channel count (256)

    IMPORTANT for Member 1: T=64 must be >= the longest ground-truth label
    length in the dataset, or CTC loss will be undefined for those samples.
    Flag this during Day 2 dataset exploration — filter or fix any label
    longer than 64 characters.
"""

import torch
import torch.nn as nn


class CNNFeatureExtractor(nn.Module):
    """Collapses (B, 1, 64, 256) -> (B, C, 1, T). See module docstring for the plan."""

    def __init__(self, channels: list[int] = None):
        super().__init__()
        channels = channels or [32, 64, 128, 128, 256]
        # TODO (Day 4): implement the actual conv/pool stack per the plan above.
        # Kept as a stub so the forward() shape contract is testable now via
        # test_model_output_shape() without a full implementation.
        self.channels = channels
        self.stub_conv = nn.Conv2d(1, channels[-1], kernel_size=1)  # placeholder only

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # STUB: real implementation replaces this in Day 4.
        # Placeholder just proves the shape contract: (B,1,64,256) -> (B,256,1,64)
        b, _, h, w = x.shape
        feat = self.stub_conv(x)
        feat = nn.functional.adaptive_avg_pool2d(feat, (1, 64))
        return feat  # (B, C, 1, T)


class SequenceModel(nn.Module):
    """BiLSTM over the CNN's sequence output."""

    def __init__(self, input_size: int, hidden_size: int = 256, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=False,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (T, B, input_size) -> (T, B, 2*hidden_size)
        out, _ = self.lstm(x)
        return out


class CRNN(nn.Module):
    def __init__(self, num_classes: int, cnn_channels: list[int] = None, hidden_size: int = 256):
        super().__init__()
        self.cnn = CNNFeatureExtractor(cnn_channels)
        feat_dim = self.cnn.channels[-1]
        self.rnn = SequenceModel(input_size=feat_dim, hidden_size=hidden_size)
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, 1, 64, 256)
        returns logits: (T, B, num_classes) — ready for nn.CTCLoss (log_softmax applied by caller)
        """
        feat = self.cnn(x)               # (B, C, 1, T)
        b, c, h, t = feat.shape
        feat = feat.squeeze(2)           # (B, C, T)
        feat = feat.permute(2, 0, 1)     # (T, B, C)
        seq = self.rnn(feat)             # (T, B, 2*hidden)
        logits = self.fc(seq)            # (T, B, num_classes)
        return logits


def build_crnn(num_classes: int, cnn_channels: list[int] = None, hidden_size: int = 256) -> nn.Module:
    """Locked interface — see shared/interfaces.md"""
    return CRNN(num_classes=num_classes, cnn_channels=cnn_channels, hidden_size=hidden_size)


if __name__ == "__main__":
    # Quick shape sanity check — run this file directly to confirm the contract holds.
    model = build_crnn(num_classes=68)  # 67 chars + blank, from charset.json
    dummy = torch.randn(4, 1, 64, 256)  # batch of 4
    out = model(dummy)
    print("Output shape:", out.shape)   # expect (64, 4, 68) -> (T, B, num_classes)
    assert out.shape[1] == 4 and out.shape[2] == 68, "Shape contract broken!"
    print("Shape contract OK.")
