# Copyright 2024 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================
"""MindSpore OpenAI ImageGPT model."""

import math
import os
import warnings
from typing import Any, Optional, Tuple, Union

import numpy as np

import mindspore as ms
from mindspore import nn, ops
from mindspore import numpy as mnp
from mindspore.nn import BCEWithLogitsLoss, CrossEntropyLoss, MSELoss
from mindspore.common.initializer import Normal

from ...activations import ACT2FN
from ...modeling_outputs import (
    BaseModelOutputWithPastAndCrossAttentions,
    CausalLMOutputWithCrossAttentions,
    SequenceClassifierOutputWithPast,
)
from ...modeling_utils import PreTrainedModel
from ...ms_utils import Conv1D, find_pruneable_heads_and_indices, prune_conv1d_layer
from ....utils import logging
from .configuration_imagegpt import ImageGPTConfig


logger = logging.get_logger(__name__)

_CHECKPOINT_FOR_DOC = "openai/imagegpt-small"
_CONFIG_FOR_DOC = "ImageGPTConfig"


def load_tf_weights_in_imagegpt(model, config, imagegpt_checkpoint_path):
    """
    Load tf checkpoints in a pytorch model
    """
    try:
        import re

        import tensorflow as tf
    except ImportError:
        logger.error(
            "Loading a TensorFlow model in PyTorch, requires TensorFlow to be installed. Please see "
            "https://www.tensorflow.org/install/ for installation instructions."
        )
        raise
    tf_path = os.path.abspath(imagegpt_checkpoint_path)
    logger.info("Converting TensorFlow checkpoint from {}".format(tf_path))
    # Load weights from TF model
    init_vars = tf.train.list_variables(tf_path)
    names = []
    arrays = []

    for name, shape in init_vars:
        logger.info("Loading TF weight {} with shape {}".format(name, shape))
        array = tf.train.load_variable(tf_path, name)
        names.append(name)
        arrays.append(array.squeeze())

    for name, array in zip(names, arrays):
        name = name[6:]  # skip "model/"
        name = name.split("/")

        # adam_v and adam_m are variables used in AdamWeightDecayOptimizer to calculated m and v
        # which are not required for using pretrained model
        if any(
            n in ["adam_v", "adam_m", "AdamWeightDecayOptimizer",
                  "AdamWeightDecayOptimizer_1", "global_step"]
            for n in name
        ) or name[-1] in ["_step"]:
            logger.info("Skipping {}".format("/".join(name)))
            continue

        pointer = model
        if name[-1] not in ["wtet"]:
            pointer = getattr(pointer, "transformer")

        for m_name in name:
            if re.fullmatch(r"[A-Za-z]+\d+", m_name):
                scope_names = re.split(r"(\d+)", m_name)
            else:
                scope_names = [m_name]

            if scope_names[0] == "w" or scope_names[0] == "g":
                pointer = getattr(pointer, "weight")
            elif scope_names[0] == "b":
                pointer = getattr(pointer, "bias")
            elif scope_names[0] == "wpe" or scope_names[0] == "wte":
                pointer = getattr(pointer, scope_names[0])
                pointer = getattr(pointer, "weight")
            elif scope_names[0] in ["q_proj", "k_proj", "v_proj"]:
                pointer = getattr(pointer, "c_attn")
                pointer = getattr(pointer, "weight")
            elif len(name) == 3 and name[1] == "attn" and scope_names[0] == "c_proj":
                pointer = getattr(pointer, scope_names[0])
                pointer = getattr(pointer, "weight")
            elif scope_names[0] == "wtet":
                pointer = getattr(pointer, "lm_head")
                pointer = getattr(pointer, "weight")
            elif scope_names[0] == "sos":
                pointer = getattr(pointer, "wte")
                pointer = getattr(pointer, "weight")
            else:
                pointer = getattr(pointer, scope_names[0])
            if len(scope_names) >= 2:
                num = int(scope_names[1])
                pointer = pointer[num]

        if len(name) > 1 and name[1] == "attn" or name[-1] == "wtet" or name[-1] == "sos" or name[-1] == "wte":
            pass  # array is used to initialize only part of the pointer so sizes won't match
        else:
            try:
                assert pointer.shape == array.shape
            except AssertionError as e:
                e.args += (pointer.shape, array.shape)
                raise

        logger.info("Initialize PyTorch weight {}".format(name))

        if name[-1] == "q_proj":
            pointer.data[:, : config.n_embd] = ms.Tensor(
                array.reshape(config.n_embd, config.n_embd)).T
        elif name[-1] == "k_proj":
            pointer.data[:, config.n_embd: 2 * config.n_embd] = ms.Tensor(
                array.reshape(config.n_embd, config.n_embd)
            ).T
        elif name[-1] == "v_proj":
            pointer.data[:, 2 * config.n_embd:] = ms.Tensor(
                array.reshape(config.n_embd, config.n_embd)).T
        elif len(name) == 3 and name[1] == "attn" and name[2] == "c_proj":
            pointer.data = ms.Tensor(
                array.reshape(config.n_embd, config.n_embd))
        elif name[-1] == "wtet":
            pointer.data = ms.Tensor(array)
        elif name[-1] == "wte":
            pointer.data[: config.vocab_size - 1, :] = ms.Tensor(array)
        elif name[-1] == "sos":
            pointer.data[-1] = ms.Tensor(array)
        else:
            pointer.data = ms.Tensor(array)

    return model


class ImageGPTLayerNorm(nn.Cell):
    def __init__(self, hidden_size: Tuple[int], eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = ms.Parameter(ms.Tensor(np.ones((hidden_size, ))))

    def construct(self, tensor: ms.Tensor) -> tuple:
        # input is not mean centered
        return (
            tensor
            / ops.sqrt(ops.mean(ops.square(tensor), axis=-1, keep_dims=True) + self.eps)
            * self.weight.data[..., :]
        )


class ImageGPTAttention(nn.Cell):
    def __init__(self, config, is_cross_attention: Optional[bool] = False, layer_idx: Optional[int] = None):
        super().__init__()

        max_positions = config.max_position_embeddings
        self.bias = ops.tril(ops.ones((max_positions, max_positions), dtype=ms.bool_)).view(
            1, 1, max_positions, max_positions
        )
        self.masked_bias = ms.Tensor(-1e4)

        self.embed_dim = config.hidden_size
        self.num_heads = config.num_attention_heads
        self.head_dim = self.embed_dim // self.num_heads
        self.split_size = self.embed_dim
        if self.head_dim * self.num_heads != self.embed_dim:
            raise ValueError(
                f"`embed_dim` must be divisible by num_heads (got `embed_dim`: {self.embed_dim} and `num_heads`:"
                f" {self.num_heads})."
            )

        self.scale_attn_weights = config.scale_attn_weights
        self.is_cross_attention = is_cross_attention

        # Layer-wise attention scaling, reordering, and upcasting
        self.scale_attn_by_inverse_layer_idx = config.scale_attn_by_inverse_layer_idx
        self.layer_idx = layer_idx
        self.reorder_and_upcast_attn = config.reorder_and_upcast_attn

        if self.is_cross_attention:
            self.c_attn = Conv1D(2 * self.embed_dim, self.embed_dim)
            self.q_attn = Conv1D(self.embed_dim, self.embed_dim)
        else:
            self.c_attn = Conv1D(3 * self.embed_dim, self.embed_dim)
        self.c_proj = Conv1D(self.embed_dim, self.embed_dim)

        self.attn_dropout = nn.Dropout(config.attn_pdrop)
        self.resid_dropout = nn.Dropout(config.resid_pdrop)

        self.pruned_heads = set()

    def prune_heads(self, heads):
        if len(heads) == 0:
            return
        heads, index = find_pruneable_heads_and_indices(
            heads, self.num_heads, self.head_dim, self.pruned_heads)
        index_attn = ops.cat(
            [index, index + self.split_size, index + (2 * self.split_size)])

        # Prune conv1d layers
        self.c_attn = prune_conv1d_layer(self.c_attn, index_attn, dim=1)
        self.c_proj = prune_conv1d_layer(self.c_proj, index, dim=0)

        # Update hyper params
        self.split_size = (self.split_size // self.num_heads) * \
            (self.num_heads - len(heads))
        self.num_heads = self.num_heads - len(heads)
        self.pruned_heads = self.pruned_heads.union(heads)

    def _attn(self, query, key, value, attention_mask=None, head_mask=None):
        attn_weights = ops.matmul(query, key.swapaxes(-1, -2))

        if self.scale_attn_weights:
            attn_weights = attn_weights / (float(value.shape[-1]) ** 0.5)

        # Layer-wise attention scaling
        if self.scale_attn_by_inverse_layer_idx:
            attn_weights = attn_weights / float(self.layer_idx + 1)

        if not self.is_cross_attention:
            # if only "normal" attention layer implements causal mask
            query_length, key_length = query.shape[-2], key.shape[-2]
            causal_mask = self.bias[:, :, key_length -
                                    query_length: key_length, :key_length]
            mask_value = np.finfo(ms.dtype_to_nptype(attn_weights.dtype)).min
            # Need to be a tensor, otherwise we get error: `RuntimeError: expected scalar type float but found double`.
            mask_value = ms.Tensor(mask_value, dtype=attn_weights.dtype)
            attn_weights = ops.where(causal_mask, attn_weights, mask_value)

        if attention_mask is not None:
            # Apply the attention mask
            attn_weights = attn_weights + attention_mask

        attn_weights = nn.Softmax(axis=-1)(attn_weights)

        # Downcast (if necessary) back to V's dtype (if in mixed-precision) -- No-Op otherwise
        attn_weights = attn_weights.type(value.dtype)
        attn_weights = self.attn_dropout(attn_weights)

        # Mask heads if we want to
        if head_mask is not None:
            attn_weights = attn_weights * head_mask

        attn_output = ops.matmul(attn_weights, value)

        return attn_output, attn_weights

    def _upcast_and_reordered_attn(self, query, key, value, attention_mask=None, head_mask=None):
        # Use `torch.baddbmm` (a bit more efficient w/ alpha param for scaling -- from Megatron-LM)
        bsz, num_heads, q_seq_len, dk = query.shape
        _, _, k_seq_len, _ = key.shape

        # Preallocate attn_weights for `baddbmm`
        attn_weights = mnp.empty((
            bsz * num_heads, q_seq_len, k_seq_len), dtype=ms.float32)

        # Compute Scale Factor
        scale_factor = 1.0
        if self.scale_attn_weights:
            scale_factor /= float(value.shape[-1]) ** 0.5

        if self.scale_attn_by_inverse_layer_idx:
            scale_factor /= float(self.layer_idx + 1)

        # Upcast (turn off autocast) and reorder (Scale K by 1 / root(dk))
        q, k = query.reshape(-1, q_seq_len,
                             dk), key.swapaxes(-1, -2).reshape(-1, dk, k_seq_len)
        attn_weights = ops.baddbmm(attn_weights, q.astype(
            ms.float32), k.astype(ms.float32), beta=0, alpha=scale_factor)
        attn_weights = attn_weights.reshape(
            bsz, num_heads, q_seq_len, k_seq_len)

        if not self.is_cross_attention:
            # if only "normal" attention layer implements causal mask
            query_length, key_length = query.shape[-2], key.shape[-2]
            causal_mask = self.bias[:, :, key_length -
                                    query_length: key_length, :key_length]
            mask_value = np.finfo(ms.dtype_to_nptype(attn_weights.dtype)).min
            # Need to be a tensor, otherwise we get error: `RuntimeError: expected scalar type float but found double`.
            mask_value = ms.Tensor(mask_value, dtype=attn_weights.dtype)
            attn_weights = ops.where(causal_mask, attn_weights, mask_value)

        if attention_mask is not None:
            # Apply the attention mask
            attn_weights = attn_weights + attention_mask

        attn_weights = nn.Softmax(axis=-1)(attn_weights)

        # Downcast (if necessary) back to V's dtype (if in mixed-precision) -- No-Op if otherwise
        if attn_weights.dtype != ms.float32:
            raise RuntimeError(
                "Error with upcasting, attn_weights does not have dtype ms.float32")
        attn_weights = attn_weights.type(value.dtype)
        attn_weights = self.attn_dropout(attn_weights)

        # Mask heads if we want to
        if head_mask is not None:
            attn_weights = attn_weights * head_mask

        attn_output = ops.matmul(attn_weights, value)

        return attn_output, attn_weights

    def _split_heads(self, tensor, num_heads, attn_head_size):
        """
        Splits hidden_size dim into attn_head_size and num_heads
        """
        new_shape = tensor.shape[:-1] + (num_heads, attn_head_size)
        tensor = tensor.view(*new_shape)
        # (batch, head, seq_length, head_features)
        return tensor.permute(0, 2, 1, 3)

    def _merge_heads(self, tensor, num_heads, attn_head_size):
        """
        Merges attn_head_size dim and num_attn_heads dim into hidden_size
        """
        tensor = tensor.permute(0, 2, 1, 3)
        new_shape = tensor.shape[:-2] + (num_heads * attn_head_size,)
        return tensor.view(new_shape)

    def construct(
        self,
        hidden_states: ms.Tensor,
        layer_past: Optional[bool] = None,
        attention_mask: Optional[ms.Tensor] = None,
        head_mask: Optional[ms.Tensor] = None,
        encoder_hidden_states: Optional[ms.Tensor] = None,
        encoder_attention_mask: Optional[ms.Tensor] = None,
        use_cache: Optional[bool] = False,
        output_attentions: Optional[bool] = False,
    ) -> tuple:
        if encoder_hidden_states is not None:
            if not hasattr(self, "q_attn"):
                raise ValueError(
                    "If class is used as cross attention, the weights `q_attn` have to be defined. "
                    "Please make sure to instantiate class with `ImageGPTAttention(..., is_cross_attention=True)`."
                )

            query = self.q_attn(hidden_states)
            key, value = self.c_attn(encoder_hidden_states).split(
                self.split_size, dim=2)
            attention_mask = encoder_attention_mask
        else:
            query, key, value = self.c_attn(hidden_states.astype(
                self.c_attn.weight.data.dtype)).split(self.split_size, axis=2)

        query = self._split_heads(query, self.num_heads, self.head_dim)
        key = self._split_heads(key, self.num_heads, self.head_dim)
        value = self._split_heads(value, self.num_heads, self.head_dim)

        if layer_past is not None:
            past_key, past_value = layer_past
            key = ops.cat((past_key, key), axis=-2)
            value = ops.cat((past_value, value), axis=-2)

        if use_cache is True:
            present = (key, value)
        else:
            present = None

        if self.reorder_and_upcast_attn:
            attn_output, attn_weights = self._upcast_and_reordered_attn(
                query, key, value, attention_mask, head_mask)
        else:
            attn_output, attn_weights = self._attn(
                query, key, value, attention_mask, head_mask)

        attn_output = self._merge_heads(
            attn_output, self.num_heads, self.head_dim)
        attn_output = self.c_proj(attn_output)
        attn_output = self.resid_dropout(attn_output)

        outputs = (attn_output, present)
        if output_attentions:
            outputs += (attn_weights,)

        return outputs  # a, present, (attentions)


class ImageGPTMLP(nn.Cell):
    def __init__(self, intermediate_size, config):
        super().__init__()
        embed_dim = config.hidden_size
        self.c_fc = Conv1D(intermediate_size, embed_dim)
        self.c_proj = Conv1D(embed_dim, intermediate_size)
        self.act = ACT2FN[config.activation_function]
        self.dropout = nn.Dropout(config.resid_pdrop)

    def construct(self, hidden_states: ms.Tensor) -> ms.Tensor:
        hidden_states = hidden_states.astype(self.c_fc.weight.data.dtype)
        hidden_states = self.c_fc(hidden_states)
        hidden_states = self.act(hidden_states)
        hidden_states = self.c_proj(hidden_states)
        hidden_states = self.dropout(hidden_states)
        return hidden_states


class ImageGPTBlock(nn.Cell):
    def __init__(self, config, layer_idx=None):
        super().__init__()
        hidden_size = config.hidden_size
        inner_dim = config.n_inner if config.n_inner is not None else 4 * hidden_size

        self.ln_1 = ImageGPTLayerNorm(
            hidden_size, eps=config.layer_norm_epsilon)
        self.attn = ImageGPTAttention(config, layer_idx=layer_idx)
        self.ln_2 = ImageGPTLayerNorm(
            hidden_size, eps=config.layer_norm_epsilon)

        if config.add_cross_attention:
            self.crossattention = ImageGPTAttention(
                config, is_cross_attention=True, layer_idx=layer_idx)
            self.ln_cross_attn = ImageGPTLayerNorm(
                hidden_size, eps=config.layer_norm_epsilon)

        self.mlp = ImageGPTMLP(inner_dim, config)

    def construct(
        self,
        hidden_states: ms.Tensor,
        layer_past: Optional[bool] = None,
        attention_mask: Optional[ms.Tensor] = None,
        head_mask: Optional[ms.Tensor] = None,
        encoder_hidden_states: Optional[ms.Tensor] = None,
        encoder_attention_mask: Optional[ms.Tensor] = None,
        use_cache: Optional[bool] = False,
        output_attentions: Optional[bool] = False,
    ) -> tuple:
        residual = hidden_states
        hidden_states = self.ln_1(hidden_states)
        attn_outputs = self.attn(
            hidden_states,
            layer_past=layer_past,
            attention_mask=attention_mask,
            head_mask=head_mask,
            use_cache=use_cache,
            output_attentions=output_attentions,
        )
        attn_output = attn_outputs[0]  # output_attn: a, present, (attentions)
        outputs = attn_outputs[1:]
        # residual connection
        hidden_states = attn_output + residual

        if encoder_hidden_states is not None:
            # add one self-attention block for cross-attention
            if not hasattr(self, "crossattention"):
                raise ValueError(
                    f"If `encoder_hidden_states` are passed, {self} has to be instantiated with "
                    "cross-attention layers by setting `config.add_cross_attention=True`"
                )
            residual = hidden_states
            hidden_states = self.ln_cross_attn(hidden_states)
            cross_attn_outputs = self.crossattention(
                hidden_states,
                attention_mask=attention_mask,
                head_mask=head_mask,
                encoder_hidden_states=encoder_hidden_states,
                encoder_attention_mask=encoder_attention_mask,
                output_attentions=output_attentions,
            )
            attn_output = cross_attn_outputs[0]
            # residual connection
            hidden_states = residual + attn_output
            # add cross attentions if we output attention weights
            outputs = outputs + cross_attn_outputs[2:]

        residual = hidden_states
        hidden_states = self.ln_2(hidden_states)
        feed_forward_hidden_states = self.mlp(hidden_states)
        # residual connection
        hidden_states = residual + feed_forward_hidden_states

        outputs = (hidden_states,) + (outputs if use_cache else outputs[1:])

        # hidden_states, present, (attentions, cross_attentions)
        return outputs


class ImageGPTPreTrainedModel(PreTrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained
    models.
    """

    config_class = ImageGPTConfig
    load_tf_weights = load_tf_weights_in_imagegpt
    base_model_prefix = "transformer"
    main_input_name = "input_ids"
    supports_gradient_checkpointing = True
    _no_split_cells = ["ImageGPTBlock"]

    def __init__(self, *inputs, **kwargs):
        super().__init__(*inputs)

    def _init_weights(self, cell):
        """Initialize the weights."""
        if isinstance(cell, (nn.Dense, Conv1D)):
            # Slightly different from the TF version which uses truncated_normal for initialization
            # cf https://github.com/pytorch/pytorch/pull/5617
            cell.weight.data.initialize(Normal(self.config.initializer_range))
            if cell.bias is not None:
                cell.bias.initialize('zeros')

        elif isinstance(cell, nn.Embedding):
            cell.weight.data.initialize(Normal(self.config.initializer_range))
            if cell.padding_idx is not None:
                cell.weight.data[cell.padding_idx].initialize('zeros')

        elif isinstance(cell, ImageGPTLayerNorm):
            cell.weight.data.fill(1.0)

        # Reinitialize selected weights subject to the OpenAI GPT-2 Paper Scheme:
        #   > A modified initialization which accounts for the accumulation on the residual path with model depth. Scale
        #   > the weights of residual layers at initialization by a factor of 1/√N where N is the # of residual layers.
        #   >   -- GPT-2 :: https://openai.com/blog/better-language-models/
        #
        # Reference (Megatron-LM): https://github.com/NVIDIA/Megatron-LM/blob/main/megatron/model/gpt_model.py
        for name, p in cell.parameters_and_names():
            if "c_proj" in name and "weight" in name:
                # Special Scaled Initialization --> There are 2 Layer Norms per Transformer Block
                p.data.initialize(
                    Normal((self.config.initializer_range / math.sqrt(2 * self.config.n_layer))))


class ImageGPTModel(ImageGPTPreTrainedModel):
    def __init__(self, config: ImageGPTConfig):
        super().__init__(config)

        self.embed_dim = config.hidden_size

        self.wte = nn.Embedding(config.vocab_size, self.embed_dim)
        self.wpe = nn.Embedding(config.max_position_embeddings, self.embed_dim)

        self.drop = nn.Dropout(config.embd_pdrop)
        self.h = nn.CellList([ImageGPTBlock(config, layer_idx=i)
                             for i in range(config.num_hidden_layers)])
        self.ln_f = ImageGPTLayerNorm(
            self.embed_dim, eps=config.layer_norm_epsilon)

        # Model parallel
        self.gradient_checkpointing = False
        # Initialize weights and apply final processing
        self.post_init()

    def get_input_embeddings(self):
        return self.wte

    def set_input_embeddings(self, new_embeddings):
        self.wte = new_embeddings

    def _prune_heads(self, heads_to_prune):
        """
        Prunes heads of the model. heads_to_prune: dict of {layer_num: list of heads to prune in this layer}
        """
        for layer, heads in heads_to_prune.items():
            self.h[layer].attn.prune_heads(heads)

    def construct(
        self,
        input_ids: Optional[ms.Tensor] = None,
        past_key_values: Optional[Tuple[Tuple[ms.Tensor]]] = None,
        attention_mask: Optional[ms.Tensor] = None,
        token_type_ids: Optional[ms.Tensor] = None,
        position_ids: Optional[ms.Tensor] = None,
        head_mask: Optional[ms.Tensor] = None,
        inputs_embeds: Optional[ms.Tensor] = None,
        encoder_hidden_states: Optional[ms.Tensor] = None,
        encoder_attention_mask: Optional[ms.Tensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        **kwargs: Any,
    ) -> Union[Tuple, BaseModelOutputWithPastAndCrossAttentions]:
        r"""
        Args:
            labels (`ms.Tensor` of shape `(batch_size, sequence_length)`, *optional*):
                Labels for language modeling. Note that the labels **are shifted** inside the model, i.e. you can set
                `labels = input_ids` Indices are selected in `[-100, 0, ..., config.vocab_size]` All labels set to `-100`
                are ignored (masked), the loss is only computed for labels in `[0, ..., config.vocab_size]`

        Returns:
            `Union[Tuple, BaseModelOutputWithPastAndCrossAttentions]`

        Example:
            ```python
            >>> from transformers import AutoImageProcessor, ImageGPTModel
            >>> from PIL import Image
            >>> import requests
            ...
            >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
            >>> image = Image.open(requests.get(url, stream=True).raw)
            ...
            >>> image_processor = AutoImageProcessor.from_pretrained("openai/imagegpt-small")
            >>> model = ImageGPTModel.from_pretrained("openai/imagegpt-small")
            ...
            >>> inputs = image_processor(images=image, return_tensors="pt")
            >>> outputs = model(**inputs)
            >>> last_hidden_states = outputs.last_hidden_state
            ```
        """

        if "pixel_values" in kwargs:
            warnings.warn(
                "The `pixel_values` argument is deprecated and will be removed in a future version, use `input_ids`"
                " instead.",
                FutureWarning,
            )

            if input_ids is not None:
                raise ValueError(
                    "You cannot pass both `pixel_values` and `input_ids`. Please make sure to only pass `input_ids`."
                )

            input_ids = kwargs.pop("pixel_values")

        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        use_cache = use_cache if use_cache is not None else self.config.use_cache
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if input_ids is not None and inputs_embeds is not None:
            raise ValueError(
                "You cannot specify both input_ids and inputs_embeds at the same time")
        elif input_ids is not None:
            self.warn_if_padding_and_no_attention_mask(
                input_ids, attention_mask)
            input_shape = input_ids.shape
            input_ids = input_ids.view(-1, input_shape[-1])
            batch_size = input_ids.shape[0]
        elif inputs_embeds is not None:
            input_shape = inputs_embeds.shape[:-1]
            batch_size = inputs_embeds.shape[0]
        else:
            raise ValueError(
                "You have to specify either input_ids or inputs_embeds")

        if token_type_ids is not None:
            token_type_ids = token_type_ids.view(-1, input_shape[-1])

        if past_key_values is None:
            past_length = 0
            past_key_values = tuple([None] * len(self.h))
        else:
            past_length = past_key_values[0][0].shape[-2]
        if position_ids is None:
            position_ids = ops.arange(
                past_length, input_shape[-1] + past_length, dtype=ms.int64)
            position_ids = position_ids.unsqueeze(0)

        # ImageGPTAttention mask.
        if attention_mask is not None:
            if batch_size <= 0:
                raise ValueError("batch_size has to be defined and > 0")
            attention_mask = attention_mask.view(batch_size, -1)
            # We create a 3D attention mask from a 2D tensor mask.
            # Sizes are [batch_size, 1, 1, to_seq_length]
            # So we can broadcast to [batch_size, num_heads, from_seq_length, to_seq_length]
            # this attention mask is more simple than the triangular masking of causal attention
            # used in OpenAI GPT, we just need to prepare the broadcast dimension here.
            attention_mask = attention_mask[:, None, None, :]

            # Since attention_mask is 1.0 for positions we want to attend and 0.0 for
            # masked positions, this operation will create a tensor which is 0.0 for
            # positions we want to attend and the dtype's smallest value for masked positions.
            # Since we are adding it to the raw scores before the softmax, this is
            # effectively the same as removing these entirely.
            attention_mask = (1.0 - attention_mask) * \
                np.finfo(ms.dtype_to_nptype(self.dtype)).min

        # If a 2D or 3D attention mask is provided for the cross-attention
        # we need to make broadcastable to [batch_size, num_heads, seq_length, seq_length]
        if self.config.add_cross_attention and encoder_hidden_states is not None:
            encoder_batch_size, encoder_sequence_length, _ = encoder_hidden_states.shape
            encoder_hidden_shape = (
                encoder_batch_size, encoder_sequence_length)
            if encoder_attention_mask is None:
                encoder_attention_mask = ops.ones(encoder_hidden_shape)
            encoder_attention_mask = self.invert_attention_mask(
                encoder_attention_mask)
        else:
            encoder_attention_mask = None

        # Prepare head mask if needed
        # 1.0 in head_mask indicate we keep the head
        # attention_probs has shape bsz x n_heads x N x N
        # head_mask has shape n_layer x batch x n_heads x N x N
        head_mask = self.get_head_mask(head_mask, self.config.n_layer)

        if inputs_embeds is None:
            inputs_embeds = self.wte(input_ids)
        position_embeds = self.wpe(position_ids)
        hidden_states = inputs_embeds + position_embeds

        if token_type_ids is not None:
            token_type_embeds = self.wte(token_type_ids)
            hidden_states = hidden_states + token_type_embeds

        hidden_states = self.drop(hidden_states)

        output_shape = input_shape + (hidden_states.shape[-1],)

        if self.gradient_checkpointing and self.training:
            if use_cache:
                logger.warning_once(
                    "`use_cache=True` is incompatible with gradient checkpointing. Setting `use_cache=False`..."
                )
                use_cache = False

        presents = () if use_cache else None
        all_self_attentions = () if output_attentions else None
        all_cross_attentions = () if output_attentions and self.config.add_cross_attention else None
        all_hidden_states = () if output_hidden_states else None
        for i, (block, layer_past) in enumerate(zip(self.h, past_key_values)):
            # Model parallel
            if output_hidden_states:
                all_hidden_states = all_hidden_states + (hidden_states,)

            if self.gradient_checkpointing and self.training:
                outputs = self._gradient_checkpointing_func(
                    block.__call__,
                    hidden_states,
                    None,
                    attention_mask,
                    head_mask[i],
                    encoder_hidden_states,
                    encoder_attention_mask,
                    use_cache,
                    output_attentions,
                )
            else:
                outputs = block(
                    hidden_states,
                    layer_past=layer_past,
                    attention_mask=attention_mask,
                    head_mask=head_mask[i],
                    encoder_hidden_states=encoder_hidden_states,
                    encoder_attention_mask=encoder_attention_mask,
                    use_cache=use_cache,
                    output_attentions=output_attentions,
                )

            hidden_states = outputs[0]
            if use_cache is True:
                presents = presents + (outputs[1],)

            if output_attentions:
                all_self_attentions = all_self_attentions + \
                    (outputs[2 if use_cache else 1],)
                if self.config.add_cross_attention:
                    all_cross_attentions = all_cross_attentions + \
                        (outputs[3 if use_cache else 2],)

        hidden_states = self.ln_f(hidden_states)

        hidden_states = hidden_states.view(*output_shape)
        # Add last hidden state
        if output_hidden_states:
            all_hidden_states = all_hidden_states + (hidden_states,)

        if not return_dict:
            return tuple(
                v
                for v in [hidden_states, presents, all_hidden_states, all_self_attentions, all_cross_attentions]
                if v is not None
            )

        return BaseModelOutputWithPastAndCrossAttentions(
            last_hidden_state=hidden_states,
            past_key_values=presents,
            hidden_states=all_hidden_states,
            attentions=all_self_attentions,
            cross_attentions=all_cross_attentions,
        )


class ImageGPTForCausalImageModeling(ImageGPTPreTrainedModel):
    _tied_weights_keys = ["lm_head.weight"]

    def __init__(self, config: ImageGPTConfig):
        super().__init__(config)
        self.transformer = ImageGPTModel(config)
        self.lm_head = nn.Dense(
            config.n_embd, config.vocab_size - 1, has_bias=False)

        # Model parallel
        # Initialize weights and apply final processing
        self.post_init()

    def get_output_embeddings(self):
        return self.lm_head

    def set_output_embeddings(self, new_embeddings):
        self.lm_head = new_embeddings

    def prepare_inputs_for_generation(self, input_ids: ms.Tensor, past_key_values: Optional[bool] = None, **kwargs):
        token_type_ids = kwargs.get("token_type_ids", None)
        # Omit tokens covered by past_key_values
        if past_key_values:
            past_length = past_key_values[0][0].shape[2]

            # Some generation methods already pass only the last input ID
            if input_ids.shape[1] > past_length:
                remove_prefix_length = past_length
            else:
                # Default to old behavior: keep only final ID
                remove_prefix_length = input_ids.shape[1] - 1

            input_ids = input_ids[:, remove_prefix_length:]
            if token_type_ids is not None:
                token_type_ids = token_type_ids[:, -input_ids.shape[1]:]

        attention_mask = kwargs.get("attention_mask", None)
        position_ids = kwargs.get("position_ids", None)

        if attention_mask is not None and position_ids is None:
            # create position_ids on the fly for batch generation
            position_ids = attention_mask.long().cumsum(-1) - 1
            position_ids = position_ids.masked_fill(attention_mask == 0, 1)
            if past_key_values:
                position_ids = position_ids[:, -input_ids.shape[1]:]
        else:
            position_ids = None
        return {
            "input_ids": input_ids,
            "past_key_values": past_key_values,
            "use_cache": kwargs.get("use_cache"),
            "position_ids": position_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }

    def construct(
        self,
        input_ids: Optional[ms.Tensor] = None,
        past_key_values: Optional[Tuple[Tuple[ms.Tensor]]] = None,
        attention_mask: Optional[ms.Tensor] = None,
        token_type_ids: Optional[ms.Tensor] = None,
        position_ids: Optional[ms.Tensor] = None,
        head_mask: Optional[ms.Tensor] = None,
        inputs_embeds: Optional[ms.Tensor] = None,
        encoder_hidden_states: Optional[ms.Tensor] = None,
        encoder_attention_mask: Optional[ms.Tensor] = None,
        labels: Optional[ms.Tensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        **kwargs: Any,
    ) -> Union[Tuple, CausalLMOutputWithCrossAttentions]:
        r"""
        Args:
            labels (`ms.Tensor` of shape `(batch_size, sequence_length)`, *optional*):
                Labels for language modeling. Note that the labels **are shifted** inside the model, i.e. you can set
                `labels = input_ids` Indices are selected in `[-100, 0, ..., config.vocab_size]` All labels set to `-100`
                are ignored (masked), the loss is only computed for labels in `[0, ..., config.vocab_size]`

        Returns:
            `Union[Tuple, CausalLMOutputWithCrossAttentions]`

        Example:
            ```python
            >>> from transformers import AutoImageProcessor, ImageGPTForCausalImageModeling
            >>> import torch
            >>> import matplotlib.pyplot as plt
            >>> import numpy as np
            ...
            >>> image_processor = AutoImageProcessor.from_pretrained("openai/imagegpt-small")
            >>> model = ImageGPTForCausalImageModeling.from_pretrained("openai/imagegpt-small")
            >>> device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            >>> model.to(device)  # doctest: +IGNORE_RESULT
            ...
            >>> # unconditional generation of 8 images
            >>> batch_size = 4
            >>> context = torch.full((batch_size, 1), model.config.vocab_size - 1)  # initialize with SOS token
            >>> context = context.to(device)
            >>> output = model.generate(
            ...     input_ids=context, max_length=model.config.n_positions + 1, temperature=1.0, do_sample=True, top_k=40
            ... )
            ...
            >>> clusters = image_processor.clusters
            >>> height = image_processor.size["height"]
            >>> width = image_processor.size["width"]
            ...
            >>> samples = output[:, 1:].cpu().detach().numpy()
            >>> samples_img = [
            ...     np.reshape(np.rint(127.5 * (clusters[s] + 1.0)), [height, width, 3]).astype(np.uint8) for s in samples
            ... ]  # convert color cluster tokens back to pixels
            >>> f, axes = plt.subplots(1, batch_size, dpi=300)
            ...
            >>> for img, ax in zip(samples_img, axes):  # doctest: +IGNORE_RESULT
            ...     ax.axis("off")
            ...     ax.imshow(img)
            ```
        """

        if "pixel_values" in kwargs:
            warnings.warn(
                "The `pixel_values` argument is deprecated and will be removed in a future version, use `input_ids`"
                " instead.",
                FutureWarning,
            )

            if input_ids is not None:
                raise ValueError(
                    "You cannot pass both `pixel_values` and `input_ids`. Please make sure to only pass `input_ids`."
                )

            input_ids = kwargs.pop("pixel_values")

        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        transformer_outputs = self.transformer(
            input_ids,
            past_key_values=past_key_values,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_attention_mask,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = transformer_outputs[0].astype(ms.float32)

        lm_logits = self.lm_head(hidden_states)

        loss = None
        if labels is not None:
            labels = labels.astype(ms.int32)
            # Shift so that tokens < n predict n
            shift_logits = lm_logits[..., :-1, :]
            shift_labels = labels[..., 1:]
            # Flatten the tokens
            loss_fct = CrossEntropyLoss()
            loss = loss_fct(
                shift_logits.view(-1, shift_logits.shape[-1]), shift_labels.view(-1))

        if not return_dict:
            output = (lm_logits,) + transformer_outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return CausalLMOutputWithCrossAttentions(
            loss=loss,
            logits=lm_logits,
            past_key_values=transformer_outputs.past_key_values,
            hidden_states=transformer_outputs.hidden_states,
            attentions=transformer_outputs.attentions,
            cross_attentions=transformer_outputs.cross_attentions,
        )

    @staticmethod
    def _reorder_cache(
        past_key_values: Tuple[Tuple[ms.Tensor]], beam_idx: ms.Tensor
    ) -> Tuple[Tuple[ms.Tensor]]:
        """
        This function is used to re-order the `past_key_values` cache if [`~PreTrainedModel.beam_search`] or
        [`~PreTrainedModel.beam_sample`] is called. This is required to match `past_key_values` with the correct
        beam_idx at every generation step.
        """
        return tuple(
            tuple(past_state.index_select(0, beam_idx)
                  for past_state in layer_past)
            for layer_past in past_key_values
        )


class ImageGPTForImageClassification(ImageGPTPreTrainedModel):
    def __init__(self, config: ImageGPTConfig):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.transformer = ImageGPTModel(config)
        self.score = nn.Dense(config.n_embd, self.num_labels, has_bias=False)

        # Initialize weights and apply final processing
        self.post_init()

    def construct(
        self,
        input_ids: Optional[ms.Tensor] = None,
        past_key_values: Optional[Tuple[Tuple[ms.Tensor]]] = None,
        attention_mask: Optional[ms.Tensor] = None,
        token_type_ids: Optional[ms.Tensor] = None,
        position_ids: Optional[ms.Tensor] = None,
        head_mask: Optional[ms.Tensor] = None,
        inputs_embeds: Optional[ms.Tensor] = None,
        labels: Optional[ms.Tensor] = None,
        use_cache: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
        **kwargs: Any,
    ) -> Union[Tuple, SequenceClassifierOutputWithPast]:
        r"""
        Args:
            labels (`ms.Tensor` of shape `(batch_size,)`, *optional*):
                Labels for computing the sequence classification/regression loss. Indices should be in `[0, ...,
                config.num_labels - 1]`. If `config.num_labels == 1` a regression loss is computed (Mean-Square loss), If
                `config.num_labels > 1` a classification loss is computed (Cross-Entropy).

        Returns:
            `Union[Tuple, SequenceClassifierOutputWithPast]`

        Example:
            ```python
            >>> from transformers import AutoImageProcessor, ImageGPTForImageClassification
            >>> from PIL import Image
            >>> import requests
            ...
            >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
            >>> image = Image.open(requests.get(url, stream=True).raw)
            ...
            >>> image_processor = AutoImageProcessor.from_pretrained("openai/imagegpt-small")
            >>> model = ImageGPTForImageClassification.from_pretrained("openai/imagegpt-small")
            ...
            >>> inputs = image_processor(images=image, return_tensors="pt")
            >>> outputs = model(**inputs)
            >>> logits = outputs.logits
            ```
        """

        if "pixel_values" in kwargs:
            warnings.warn(
                "The `pixel_values` argument is deprecated and will be removed in a future version, use `input_ids`"
                " instead.",
                FutureWarning,
            )

            if input_ids is not None:
                raise ValueError(
                    "You cannot pass both `pixel_values` and `input_ids`. Please make sure to only pass `input_ids`."
                )

            input_ids = kwargs.pop("pixel_values")

        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        transformer_outputs = self.transformer(
            input_ids,
            past_key_values=past_key_values,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            use_cache=use_cache,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = transformer_outputs[0].astype(ms.float32)
        # average-pool the hidden states along the sequence dimension
        pooled_hidden_states = hidden_states.mean(axis=1)
        # project from (batch_size, hidden_size) to (batch_size, num_labels)
        logits = self.score(pooled_hidden_states)

        loss = None
        if labels is not None:
            labels = labels.astype(ms.int32)
            if self.config.problem_type is None:
                if self.num_labels == 1:
                    self.config.problem_type = "regression"
                elif self.num_labels > 1 and (labels.dtype in (ms.int64, ms.int32)):
                    self.config.problem_type = "single_label_classification"
                else:
                    self.config.problem_type = "multi_label_classification"

            if self.config.problem_type == "regression":
                loss_fct = MSELoss()
                if self.num_labels == 1:
                    loss = loss_fct(logits.squeeze(), labels.squeeze())
                else:
                    loss = loss_fct(logits, labels)
            elif self.config.problem_type == "single_label_classification":
                loss_fct = CrossEntropyLoss()

                l_result = logits.view(-1, self.num_labels)
                lab = labels.view(-1)

                loss = loss_fct(l_result, lab)
            elif self.config.problem_type == "multi_label_classification":
                loss_fct = BCEWithLogitsLoss()
                loss = loss_fct(logits, labels)
        if not return_dict:
            output = (logits,) + transformer_outputs[1:]
            return ((loss,) + output) if loss is not None else output

        return SequenceClassifierOutputWithPast(
            loss=loss,
            logits=logits,
            past_key_values=transformer_outputs.past_key_values,
            hidden_states=transformer_outputs.hidden_states,
            attentions=transformer_outputs.attentions,
        )


__all__ = [
    "ImageGPTModel",
    "ImageGPTForImageClassification",
    "ImageGPTForCausalImageModeling"
]
