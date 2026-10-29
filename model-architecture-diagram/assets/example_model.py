"""Teaching fixture only: tiny causal decoder; untrained, no RoPE and no KV cache.

Reading this file does not require PyTorch. Executing it requires PyTorch >= 2.4.
Tensor convention: [B, T, D]; model dimensions are intentionally small.
"""
from dataclasses import dataclass
import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class Config:
    vocab_size: int = 1024
    hidden_size: int = 256
    num_heads: int = 4
    intermediate_size: int = 768
    num_layers: int = 2


class Attention(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.heads = c.num_heads
        self.head_dim = c.hidden_size // c.num_heads
        self.q = nn.Linear(c.hidden_size, c.hidden_size, bias=False)
        self.k = nn.Linear(c.hidden_size, c.hidden_size, bias=False)
        self.v = nn.Linear(c.hidden_size, c.hidden_size, bias=False)
        self.out = nn.Linear(c.hidden_size, c.hidden_size, bias=False)

    def forward(self, x):
        b, t, d = x.shape
        q, k, v = [proj(x).view(b, t, self.heads, self.head_dim).transpose(1, 2)
                   for proj in (self.q, self.k, self.v)]
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.out(a.transpose(1, 2).contiguous().view(b, t, d))


class MLP(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.gate = nn.Linear(c.hidden_size, c.intermediate_size, bias=False)
        self.up = nn.Linear(c.hidden_size, c.intermediate_size, bias=False)
        self.down = nn.Linear(c.intermediate_size, c.hidden_size, bias=False)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.norm1, self.norm2 = nn.RMSNorm(c.hidden_size), nn.RMSNorm(c.hidden_size)
        self.attention, self.mlp = Attention(c), MLP(c)

    def forward(self, x):
        x = x + self.attention(self.norm1(x))
        return x + self.mlp(self.norm2(x))


class TinyDecoder(nn.Module):
    def __init__(self, c=None):
        super().__init__()
        c = c or Config()
        self.embedding = nn.Embedding(c.vocab_size, c.hidden_size)
        self.blocks = nn.ModuleList([Block(c) for _ in range(c.num_layers)])
        self.norm = nn.RMSNorm(c.hidden_size)
        self.head = nn.Linear(c.hidden_size, c.vocab_size, bias=False)

    def forward(self, input_ids):
        x = self.embedding(input_ids)
        for block in self.blocks:
            x = block(x)
        return self.head(self.norm(x))
