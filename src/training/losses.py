import torch
import torch.nn as nn

ctc = nn.CTCLoss(blank=0, zero_infinity=True)


def ctc_loss(logits: torch.Tensor, targets: torch.Tensor,
             input_lengths: torch.Tensor, target_lengths: torch.Tensor) -> torch.Tensor:
    """logits: (T,B,num_classes) raw scores. Applies log_softmax internally."""
    log_probs = logits.log_softmax(dim=2)
    return ctc(log_probs, targets, input_lengths, target_lengths)
