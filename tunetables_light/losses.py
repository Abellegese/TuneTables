import torch
from torch import nn


class Losses:
    gaussian = nn.GaussianNLLLoss(full=True, reduction="none")
    mse = nn.MSELoss(reduction="none")

    def ce(num_classes):
        num_classes = (
            num_classes.shape[0] if torch.is_tensor(num_classes) else num_classes
        )
        return nn.CrossEntropyLoss(reduction="none", weight=torch.ones(num_classes))

    bce = nn.BCEWithLogitsLoss(reduction="none")


class CrossEntropyForMulticlassLoss(torch.nn.CrossEntropyLoss):
    # This loss applies cross entropy after reducing the number of prediction
    # dimensions to the number of classes in the target

    # TODO: loss.item() doesn't work so the displayed losses are Nans
    def __init__(
        self,
        num_classes,
        weight=None,
        size_average=None,
        ignore_index: int = -100,
        reduce=None,
        reduction: str = "mean",
        label_smoothing: float = 0.0,
    ) -> None:
        super().__init__(
            size_average=size_average,
            reduce=reduce,
            reduction=reduction,
            ignore_index=ignore_index,
        )
        self.num_classes = num_classes

    def forward(self, input: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        loss = torch.zeros_like(input[:, :, 0])
        for b in range(target.shape[1]):
            l = super().forward(
                input[:, b, 0 : len(torch.unique(target[:, b]))], target[:, b]
            )
            loss[:, b] += l
        return loss.flatten()


def JointBCELossWithLogits(output, target):
    # output shape: (S, B, NS) with NS = Number of sequences
    # target shape: (S, B, SL)
    # Loss = -log(mean_NS(prod_SL(p(target_SL, output_NS))))
    # Here at the moment NS = SL
    output = output.unsqueeze(-1).repeat(1, 1, 1, target.shape[-1])  # (S, B, NS, SL)
    output = output.permute(2, 0, 1, 3)  # (NS, S, B, SL)
    print(target.shape, output.shape)
    loss = (target * torch.sigmoid(output)) + (
        (1 - target) * (1 - torch.sigmoid(output))
    )
    loss = loss.prod(-1)
    loss = loss.mean(0)
    loss = -torch.log(loss)
    loss = loss.mean()
    return loss


class ScaledSoftmaxCE(nn.Module):
    def forward(self, x, label):
        logits = x[..., :-10]
        temp_scales = x[..., -10:]

        logprobs = logits.softmax(-1)


def kl_divergence(clf_out_a, clf_out_b, reduction="mean"):
    assert clf_out_a.shape == clf_out_b.shape
    kl_divs_per_example = torch.sum(
        torch.nn.functional.softmax(clf_out_a, dim=1)
        * (
            torch.nn.functional.log_softmax(clf_out_a, dim=1)
            - torch.nn.functional.log_softmax(clf_out_b, dim=1)
        ),
        dim=1,
    )
    if reduction == "mean":
        kl_div = torch.mean(kl_divs_per_example)
    elif reduction == "sum":
        kl_div = torch.sum(kl_divs_per_example)
    else:
        assert reduction is None or reduction == "none"
        kl_div = kl_divs_per_example
    return kl_div
