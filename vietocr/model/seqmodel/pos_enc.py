import math
from typing import Optional
import torch.nn as nn
import torch

class ImgPosEnc(nn.Module):
    """
    This is a more standard version of the position embedding, very similar to the one
    used by the Attention is all you need paper, generalized to work on images.
    """

    def __init__(
        self,
        d_model: int = 512,
        temperature: float = 10000.0,
        normalize: bool = False,
        scale: Optional[float] = None,
    ):
        super().__init__()
        assert d_model % 2 == 0
        self.half_d_model = d_model // 2
        self.temperature = temperature
        self.normalize = normalize
        if scale is not None and normalize is False:
            raise ValueError("normalize should be True if scale is passed")
        if scale is None:
            scale = 2 * math.pi
        self.scale = scale

    def forward(self, x: torch.Tensor, mask: torch.LongTensor) -> torch.Tensor:
        """add image positional encoding to feature

        Parameters
        ----------
        x : torch.Tensor
            [b, h, w, d]
        mask: torch.LongTensor
            [b, h, w]

        Returns
        -------
        torch.Tensor
            [b, h, w, d]
        """
        not_mask = ~mask
        y_embed = not_mask.cumsum(1, dtype=torch.float32)
        x_embed = not_mask.cumsum(2, dtype=torch.float32)
        if self.normalize:
            eps = 1e-6
            y_embed = y_embed / (y_embed[:, -1:, :] + eps) * self.scale
            x_embed = x_embed / (x_embed[:, :, -1:] + eps) * self.scale

        # not exactly the same as concat two WordPosEnc
        # WordPosEnc: sin(0), cos(0), sin(2), cos(2)
        # ImagePosEnc: sin(0), cos(1), sin(2), cos(3)
        dim_t = torch.arange(self.half_d_model, dtype=torch.float, device=self.device)
        inv_feq = 1.0 / (self.temperature ** (dim_t / self.half_d_model))

        pos_x = torch.einsum("b h w, d -> b h w d", x_embed, inv_feq)
        pos_y = torch.einsum("b h w, d -> b h w d", y_embed, inv_feq)

        pos_x = torch.stack(
            (pos_x[:, :, :, 0::2].sin(), pos_x[:, :, :, 1::2].cos()), dim=4
        ).flatten(3)
        pos_y = torch.stack(
            (pos_y[:, :, :, 0::2].sin(), pos_y[:, :, :, 1::2].cos()), dim=4
        ).flatten(3)
        pos = torch.cat((pos_x, pos_y), dim=3)

        x = x + pos
        return x
