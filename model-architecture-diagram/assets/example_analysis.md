# Tiny Decoder 示例结构分析

这是本技能自编的教学模型，不是 InfraTech 或其他机构发布的模型。源代码位于 `assets/example_model.py`。本图基于静态阅读，未训练，也未执行 PyTorch 模型，不声称有实际性能。

默认 Config：词表 1024，D=256，H=4，dh=D/H=64（推导），FFN 中间维 768，2 个同构 block。输入 `[B,T]`，Embedding 后 `[B,T,256]`。每个 block 是 `x += Attention(RMSNorm(x))`，接着 `x += MLP(RMSNorm(x))`；最终 Norm、独立 LM Head 输出 `[B,T,1024]`。没有权重绑定、位置编码、RoPE、MoE、KV cache 或训练辅助头。

Attention：三个独立无 bias 投影，reshape/transpose 为 `[B,4,T,64]`，调用带 causal mask 的 SDPA，合并 heads 后输出投影。图中 SDPA 的 softmax 公式是此标准算子的数学展开，缩放 `√64` 根据 dh=64 推导，mask 禁止看未来 token；不代表 Python 中存在显式 Softmax 模块。MLP 为 `down(silu(gate(x))*up(x))`。

SDPA 的标准缩放、因果遮罩和输出语义另核对了 [PyTorch 官方说明](https://docs.pytorch.org/docs/2.15/generated/torch.nn.functional.scaled_dot_product_attention.html)。

图中只展开一个代表 block 的内部，虚线容器的 ×2 表示按序重复，不表示参数共享。实线箭头是计算，彩色无箭头虚线只是展开关系。

风格参考：[InfraTech/models](https://github.com/CalvinXKY/InfraTech/tree/48e358a4b5119c24cf472adc64d0b4f86f894e99/models)，commit `48e358a4b5119c24cf472adc64d0b4f86f894e99`。布局、模板、代码均在本技能中重新制作；未复制原图。

## 图中元素的证据

| ID | 结构或关系 | 来源 | 状态 |
| --- | --- | --- | --- |
| `input_ids` | Input IDs · [B, T] | `assets/example_model.py:70-71` | 静态代码确认；尺寸由配置推导 |
| `embedding` | Embedding | `assets/example_model.py:65,71` | 静态代码确认；尺寸由配置推导 |
| `norm1` | RMSNorm | `assets/example_model.py:53,57` | 静态代码确认；尺寸由配置推导 |
| `attention` | Self-Attention | `assets/example_model.py:54,57` | 静态代码确认；尺寸由配置推导 |
| `norm2` | RMSNorm | `assets/example_model.py:53,58` | 静态代码确认；尺寸由配置推导 |
| `mlp` | SwiGLU MLP | `assets/example_model.py:54,58` | 静态代码确认；尺寸由配置推导 |
| `final_norm` | RMSNorm | `assets/example_model.py:67,74` | 静态代码确认；尺寸由配置推导 |
| `head` | LM Head | `assets/example_model.py:68,74` | 静态代码确认；尺寸由配置推导 |
| `add1` | add | `assets/example_model.py:57` | 静态代码确认；尺寸由配置推导 |
| `add2` | add | `assets/example_model.py:58` | 静态代码确认；尺寸由配置推导 |
| `up` | Linear (up) | `assets/example_model.py:43` | 静态代码确认；尺寸由配置推导 |
| `gate` | Linear (gate) | `assets/example_model.py:42` | 静态代码确认；尺寸由配置推导 |
| `silu` | SiLU | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `product` | multiply | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `down` | Linear (down) | `assets/example_model.py:44` | 静态代码确认；尺寸由配置推导 |
| `q` | Linear (Q) | `assets/example_model.py:26,33-34` | 静态代码确认；尺寸由配置推导 |
| `k` | Linear (K) | `assets/example_model.py:27,33-34` | 静态代码确认；尺寸由配置推导 |
| `v` | Linear (V) | `assets/example_model.py:28,33-34` | 静态代码确认；尺寸由配置推导 |
| `reshape` | Reshape + Transpose (Q, K, V) | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `sdpa` | SDPA · causal mask; softmax(QKᵀ / √64 + mask) V | `assets/example_model.py:35` | 标准 SDPA 数学展开，尺寸为推导 |
| `merge` | Transpose + Merge Heads | `assets/example_model.py:36` | 静态代码确认；尺寸由配置推导 |
| `out_proj` | Linear (output) | `assets/example_model.py:29,36` | 静态代码确认；尺寸由配置推导 |
| `input_to_emb` | 数据流/残差连接 | `assets/example_model.py:71` | 静态代码确认；尺寸由配置推导 |
| `emb_to_norm` | 数据流/残差连接 | `assets/example_model.py:57,71-73` | 静态代码确认；尺寸由配置推导 |
| `norm_to_attention` | 数据流/残差连接 | `assets/example_model.py:57` | 静态代码确认；尺寸由配置推导 |
| `attention_to_add` | 数据流/残差连接 | `assets/example_model.py:57` | 静态代码确认；尺寸由配置推导 |
| `add_to_norm2` | 数据流/残差连接 | `assets/example_model.py:58` | 静态代码确认；尺寸由配置推导 |
| `norm2_to_mlp` | 数据流/残差连接 | `assets/example_model.py:58` | 静态代码确认；尺寸由配置推导 |
| `mlp_to_add` | 数据流/残差连接 | `assets/example_model.py:58` | 静态代码确认；尺寸由配置推导 |
| `blocks_to_final` | 数据流/残差连接 | `assets/example_model.py:72-74` | 静态代码确认；尺寸由配置推导 |
| `norm_to_head` | 数据流/残差连接 | `assets/example_model.py:74` | 静态代码确认；尺寸由配置推导 |
| `residual_attention` | 数据流/残差连接 | `assets/example_model.py:57` | 静态代码确认；尺寸由配置推导 |
| `residual_mlp` | 数据流/残差连接 | `assets/example_model.py:58` | 静态代码确认；尺寸由配置推导 |
| `logits` | [B, T, 1024] | `assets/example_model.py:68,74` | 静态代码确认；尺寸由配置推导 |
| `mlp_input` | 数据流/残差连接 | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `mlp_gate_input` | 数据流/残差连接 | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `gate_to_silu` | 数据流/残差连接 | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `up_to_product` | 数据流/残差连接 | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `silu_to_product` | 数据流/残差连接 | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `product_to_down` | [B, T, 768] | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `mlp_output` | [B, T, 256] | `assets/example_model.py:47` | 静态代码确认；尺寸由配置推导 |
| `attention_input` | 数据流/残差连接 | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `attention_k_input` | 数据流/残差连接 | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `attention_v_input` | 数据流/残差连接 | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `q_to_reshape` | 数据流/残差连接 | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `k_to_reshape` | 数据流/残差连接 | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `v_to_reshape` | 数据流/残差连接 | `assets/example_model.py:33-34` | 静态代码确认；尺寸由配置推导 |
| `reshape_to_sdpa` | Q / K / V: [B, 4, T, 64] | `assets/example_model.py:33-35` | 静态代码确认；尺寸由配置推导 |
| `sdpa_to_merge` | [B, 4, T, 64] | `assets/example_model.py:35-36` | 静态代码确认；尺寸由配置推导 |
| `merge_to_out` | [B, T, 256] | `assets/example_model.py:36` | 静态代码确认；尺寸由配置推导 |
| `attention_output` | [B, T, 256] | `assets/example_model.py:36` | 静态代码确认；尺寸由配置推导 |
