# coding=utf-8
# Copyright 2022 Meta Platforms authors and The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""MindSpore FLAVA model."""

import collections
import math
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import mindspore
from mindnlp.core import nn, ops

from ...activations import ACT2FN
from ...modeling_outputs import BaseModelOutput, BaseModelOutputWithPooling
from ...modeling_utils import PreTrainedModel
from ...ms_utils import find_pruneable_heads_and_indices, prune_linear_layer
from ....utils import (
    ModelOutput,
    logging,
)
from .configuration_flava import (
    FlavaConfig,
    FlavaImageCodebookConfig,
    FlavaImageConfig,
    FlavaMultimodalConfig,
    FlavaTextConfig,
)


logger = logging.get_logger(__name__)

_CHECKPOINT_FOR_DOC = "facebook/flava-full"

# Codebook docstring
_CHECKPOINT_FOR_CODEBOOK_DOC = "facebook/flava-image-codebook"
_CONFIG_CLASS_FOR_IMAGE_MODEL_DOC = "FlavaImageConfig"
_CONFIG_CLASS_FOR_TEXT_MODEL_DOC = "FlavaTextConfig"
_CONFIG_CLASS_FOR_MULTIMODAL_MODEL_DOC = "FlavaMultimodalConfig"
_EXPECTED_IMAGE_OUTPUT_SHAPE = [1, 197, 768]


LOGIT_SCALE_CLAMP_MIN = 0
LOGIT_SCALE_CLAMP_MAX = 4.6052

FlavaPossibleConfigs = Union[FlavaTextConfig, FlavaImageConfig, FlavaMultimodalConfig]


@dataclass
class FlavaModelOutput(ModelOutput):
    """
    Output from FlavaModel containing embeddings and outputs from individual encoders.

    Note that `image_embeddings` and `text_embeddigns` returned are similar to pooled output returned from a
    transformer. If you want embeddings for contrastive loss or retrieval use a FLAVA model's `image_projection` and
    `text_projection` layers on `image_embeddings` and `text_embeddings` respectively.

    Args:
        image_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `pixel_values` are present):
            The image embeddings which are basically the pooled output of [`FlavaImageModel`].
        image_output (`BaseModelOutputWithPooling`, *optional*, returned when `pixel_values` are present):
            The output of the [`FlavaImageModel`].
        text_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `input_ids` are present):
            The text embeddings which are basically the pooled output of [`FlavaTextModel`].
        text_output (`BaseModelOutputWithPooling`, *optional*, returned when `input_ids` are present):
            The output of the [`FlavaTextModel`].
        multimodal_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `input_ids` and `pixel_values` are present and `skip_multimodal_encoder` is `None` or `False`):
            The multimodal embeddings which are basically the pooled output of [`FlavaTextModel`].
        multimodal_output (`BaseModelOutputWithPooling`, returned when `input_ids` and `pixel_values` are present and `skip_multimodal_encoder` is `None` or `False`):
            The output of the [`FlavaMultimodalModel`].
    """

    image_embeddings: Optional[mindspore.Tensor] = None
    image_output: Optional[BaseModelOutputWithPooling] = None
    text_embeddings: Optional[mindspore.Tensor] = None
    text_output: Optional[BaseModelOutputWithPooling] = None
    multimodal_embeddings: Optional[mindspore.Tensor] = None
    multimodal_output: Optional[BaseModelOutputWithPooling] = None

    def to_tuple(self) -> Tuple[Any]:
        return tuple(
            self[k] if k not in ["text_output", "image_output", "multimodal_output"] else getattr(self, k).to_tuple()
            for k in self.keys()
        )


@dataclass
class FlavaLosses(ModelOutput):
    """Class representing pretraining losses from FLAVA model

    Args:
        mim (`mindspore.Tensor` of shape `(1,)`, *optional*, returned when `mim_labels` and `pixel_values` are present, `input_ids_masked` is absent and `mim_weight` > 0.:
            Masked Image Modeling loss as used in BeIT calculated only for unimodal image data.
        mlm (`mindspore.Tensor` of shape `(1,)`, *optional*, returned when `mlm_labels` and `input_ids_masked` are present, `pixel_values` is absent and `mlm_weight` > 0.:
            Masked Language Modeling loss as used in BERT calculated only for unimodal text data.
        itm (`mindspore.Tensor` of shape `(1,)`, *optional*, returned when `itm_labels`, `input_ids_masked`, `pixel_values` are present and `itm_weight` > 0.:
            Image Text Matching (ITM) loss calculated for paired image-text data. Note that ITM loss is calculated on
            masked pairs in FLAVA.
        global_contrastive (`mindspore.Tensor` of shape `(1,)`, *optional*, returned when `input_ids` and `pixel_values` are present and `global_contrastive_weight` > 0.:
            Contrastive loss for image-text similarity similar to CLIP but calculated globally for paired image-text
            data. This is calculated on unmasked images and texts.
        mmm_image (`mindspore.Tensor` of shape `(1,)`, *optional*, returned when `mim_labels`, `pixel_values` and `input_ids_masked` are present and `mmm_image_weight` > 0.:
            Masked Multimodal Modeling loss's image component calculated on paired image-text data.
        mmm_text (`mindspore.Tensor` of shape `(1,)`, *optional*, returned when `mlm_labels`, `pixel_values` and `input_ids_masked` are present and `mmm_text_weight` > 0.:
            Masked Multimodal Modeling loss's text component calculated on paired image-text data.
    """

    mim: Optional[mindspore.Tensor] = None
    mlm: Optional[mindspore.Tensor] = None
    itm: Optional[mindspore.Tensor] = None
    global_contrastive: Optional[mindspore.Tensor] = None
    mmm_image: Optional[mindspore.Tensor] = None
    mmm_text: Optional[mindspore.Tensor] = None

    def all_none(self) -> bool:
        all_none = True
        for v in self.values():
            if v is not None:
                all_none = False
                break
        return all_none


@dataclass
class FlavaForPreTrainingOutput(ModelOutput):
    """
    Output from FlavaForPreTraining containing embeddings, and outputs from individual encoders.

    Note that `image_embeddings` and `text_embeddings` returned are similar to pooled output returned from a
    transformer. If you want embeddings for contrastive loss or retrieval use a FLAVA model's `image_projection` and
    `text_projection` layers on `image_embeddings` and `text_embeddings` respectively.

    Args:
        loss (`mindspore.Tensor`, *optional*, returned when `return_loss` is True):
            Total loss calculated for this model.
        loss_info (`FlavaLosses`):
            Detailed info for FLAVA Pretraining losses. Check `FlavaLosses` class description for the information on
            the keys.
        image_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `pixel_values` are present):
            The image embeddings which are basically the pooled output of [`FlavaImageModel`].
        image_output (`BaseModelOutputWithPooling`, *optional*, returned when `pixel_values` are present):
            The output of the [`FlavaImageModel`].
        text_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `input_ids` are present):
            The text embeddings which are basically the pooled output of [`FlavaTextModel`].
        text_output (`BaseModelOutputWithPooling`, *optional*, returned when `input_ids` are present):
            The output of the [`FlavaTextModel`].
        multimodal_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `input_ids` and `pixel_values` are present and `skip_unmasked_multimodal_encoder` is `None` or `False`):
            The multimodal embeddings which are basically the pooled output of [`FlavaTextModel`].
        multimodal_output (`BaseModelOutputWithPooling`, returned when `input_ids` and `pixel_values` are present and `skip_unmasked_multimodal_encoder` is `None` or `False`):
            The output of the [`FlavaMultimodalModel`].

        image_masked_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `pixel_values` are present):
            The image embeddings which are basically the pooled output of [`FlavaImageModel`]. Uses `bool_masked_pos`
            to create masked images.
        image_masked_output (`BaseModelOutputWithPooling`, *optional*, returned when `pixel_values` are present):
            The output of the [`FlavaImageModel`]. Uses `bool_masked_pos` to create masked images.
        text_masked_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `input_ids_masked` are present):
            The text embeddings which are basically the pooled output of [`FlavaTextModel`].
        text_masked_output (`BaseModelOutputWithPooling`, *optional*, returned when `input_ids_masked` are present):
            The output of the [`FlavaTextModel`].
        multimodal_masked_embeddings (`mindspore.Tensor` of shape `(batch_size, output_dim)`, *optional*, returned when `input_ids` and `pixel_values` are present):
            The multimodal embeddings which are basically the pooled output of [`FlavaTextModel`].
        multimodal_masked_output (`BaseModelOutputWithPooling`, *optional*, returned when `input_ids_masked` and `pixel_values` are present):
            The output of the [`FlavaMultimodalModel`].

        mim_logits (`mindspore.Tensor` of shape `(batch_size, num_image_patches, image_vocab_size)` or of shape `(total_masked_patches, image_vocab_size)` , *optional*, returned when `pixel_values` are present and `input_ids_masked` are not):
                The logits for MIM unimodal loss. Uses `book_masked_pos` to get masked patches. The flattened output is
                returned when `bool_masked_pos` has some of the patches masked.
        mlm_logits (`mindspore.Tensor` of shape `(batch_size, text_seq_length, text_vocab_size)` or of shape `(total_masked_seq_length, text_vocab_size)`, *optional*, returned when `input_ids_masked` are present and `pixel_values` are not):
                The logits for MLM unimodal loss. The flattened output is returned when `input_ids_masked` has some of
                the tokens masked.
        itm_logits (`mindspore.Tensor` of shape `(batch_size, 2)`, *optional*, returned when `input_ids_masked` and `pixel_values` are present):
                The logits for ITM loss. Note that ITM loss is calculated on masked pairs in FLAVA.
        mmm_image_logits (`mindspore.Tensor` of shape `(batch_size, num_image_patches, image_vocab_size)` or of shape`(total_masked_patches, image_vocab_size)`, *optional*, returned when `pixel_values` and `input_ids_masked` are present):
                The logits for MMM image multimodal loss. Uses `book_masked_pos` to get masked patches. The flattened
                output is returned when `bool_masked_pos` has some of the patches masked.
        mmm_text_logits (`mindspore.Tensor` of shape `(batch_size, text_seq_length, text_vocab_size)` or of shape `(`(total_masked_seq_length, text_vocab_size)`), *optional*, returned when `pixel_values` and `input_ids_masked` are present):
                The logits for MMM text multimodal loss. The flattened output is returned when `input_ids_masked` has
                some of the tokens masked.
        contrastive_logits_per_image (`mindspore.Tensor` of shape `(image_batch_size, text_batch_size)`):
            The scaled dot product scores between `image_embeddings` and `text_embeddings` but passed through FLAVA's
            `image_projection` and `text_projection` layers respectively. This represents the image-text similarity
            scores. This is calculated on unmasked images and texts.
        contrastive_logits_per_text (`mindspore.Tensor` of shape `(text_batch_size, image_batch_size)`):
            The scaled dot product scores between `text_embeddings` and `image_embeddings` but passed through FLAVA's
            `text_projection` and `image_projection` layers respectively. This is calculated on unmasked images and
            texts.
    """

    loss: Optional[mindspore.Tensor] = None
    loss_info: FlavaLosses = None
    image_embeddings: Optional[mindspore.Tensor] = None
    image_output: Optional[BaseModelOutputWithPooling] = None
    text_embeddings: Optional[mindspore.Tensor] = None
    text_output: Optional[BaseModelOutputWithPooling] = None
    multimodal_embeddings: Optional[mindspore.Tensor] = None
    multimodal_output: Optional[BaseModelOutputWithPooling] = None
    image_masked_embeddings: Optional[mindspore.Tensor] = None
    image_masked_output: Optional[BaseModelOutputWithPooling] = None
    text_masked_embeddings: Optional[mindspore.Tensor] = None
    text_masked_output: Optional[BaseModelOutputWithPooling] = None
    multimodal_masked_embeddings: Optional[mindspore.Tensor] = None
    multimodal_masked_output: Optional[BaseModelOutputWithPooling] = None
    mim_logits: Optional[mindspore.Tensor] = None
    mlm_logits: Optional[mindspore.Tensor] = None
    itm_logits: Optional[mindspore.Tensor] = None
    contrastive_logits_per_image: Optional[mindspore.Tensor] = None
    contrastive_logits_per_text: Optional[mindspore.Tensor] = None
    mmm_image_logits: Optional[mindspore.Tensor] = None
    mmm_text_logits: Optional[mindspore.Tensor] = None

    def to_tuple(self) -> Tuple[Any]:
        transformer_outputs = [
            "text_output",
            "image_output",
            "multimodal_output",
            "text_masked_output",
            "image_masked_output",
            "multimodal_masked_output",
        ]
        return tuple(self[k] if k not in transformer_outputs else getattr(self, k).to_tuple() for k in self.keys())


# Based on timm implementation, which can be found here:
# https://github.com/rwightman/pytorch-image-models/blob/master/timm/models/image_transformer.py
class FlavaImageEmbeddings(nn.Module):
    """
    Construct the CLS token, position and patch embeddings. Optionally, also the mask token.
    """

    def __init__(self, config: FlavaImageConfig, use_mask_token: bool = False) -> None:
        super().__init__()

        use_mask_token = use_mask_token or config.mask_token
        self.cls_token = nn.Parameter(ops.zeros(1, 1, config.hidden_size))
        self.mask_token = nn.Parameter(ops.zeros(1, 1, config.hidden_size)) if use_mask_token else None
        self.patch_embeddings = PatchEmbeddings(
            image_size=config.image_size,
            patch_size=config.patch_size,
            num_channels=config.num_channels,
            embed_dim=config.hidden_size,
        )
        num_patches = self.patch_embeddings.num_patches
        self.position_embeddings = nn.Parameter(ops.zeros(1, num_patches + 1, config.hidden_size))
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.config = config

    def interpolate_pos_encoding(self, embeddings: mindspore.Tensor, height: int, width: int) -> mindspore.Tensor:
        """
        This method allows to interpolate the pre-trained position encodings, to be able to use the model on higher
        resolution images.

        Source:
        https://github.com/facebookresearch/dino/blob/de9ee3df6cf39fac952ab558447af1fa1365362a/image_transformer.py#L174
        """

        npatch = embeddings.shape[1] - 1
        num_pos = self.position_embeddings.shape[1] - 1
        if npatch == num_pos and height == width:
            return self.position_embeddings
        class_pos_embed = self.position_embeddings[:, 0]
        patch_pos_embed = self.position_embeddings[:, 1:]
        dim = embeddings.shape[-1]
        num_h_patches = height // self.config.patch_size
        num_w_patches = width // self.config.patch_size
        # we add a small number to avoid floating point error in the interpolation
        # see discussion at https://github.com/facebookresearch/dino/issues/8
        num_h_patches, num_w_patches = num_h_patches + 0.1, num_w_patches + 0.1
        patch_pos_embed = nn.functional.interpolate(
            patch_pos_embed.reshape(1, int(math.sqrt(num_pos)), int(math.sqrt(num_pos)), dim).permute(0, 3, 1, 2),
            scale_factor=(num_h_patches / math.sqrt(num_pos), num_w_patches / math.sqrt(num_pos)),
            mode="bicubic",
            align_corners=False,
        )
        if int(num_h_patches) != patch_pos_embed.shape[-2] or int(num_w_patches) != patch_pos_embed.shape[-1]:
            raise ValueError(
                f"Number of patches for images ({int(num_h_patches), int(num_w_patches)}) don't match the "
                f"shape of position embedding ({patch_pos_embed.shape[-2], patch_pos_embed.shape[-1]})"
            )
        patch_pos_embed = patch_pos_embed.permute(0, 2, 3, 1).view(1, -1, dim)
        return ops.cat((class_pos_embed.unsqueeze(0), patch_pos_embed), dim=1)

    def forward(
        self,
        pixel_values: mindspore.Tensor,
        bool_masked_pos: Optional[mindspore.Tensor] = None,
        interpolate_pos_encoding: bool = False,
    ) -> mindspore.Tensor:
        batch_size, num_channels, height, width = pixel_values.shape
        embeddings = self.patch_embeddings(pixel_values, interpolate_pos_encoding=interpolate_pos_encoding)

        batch_size, seq_len, _ = embeddings.shape
        if bool_masked_pos is not None:
            mask_tokens = self.mask_token.broadcast_to((batch_size, seq_len, -1))
            # B X H X W = B X HW
            if bool_masked_pos.dim() == 3:
                bool_masked_pos = bool_masked_pos.view(bool_masked_pos.shape[0], -1)
            # replace the masked visual tokens by mask_tokens
            mask = bool_masked_pos.unsqueeze(-1).type_as(mask_tokens)
            embeddings = embeddings * (1.0 - mask) + mask_tokens * mask

        # add the [CLS] token to the embedded patch tokens
        cls_tokens = self.cls_token.broadcast_to((batch_size, -1, -1))
        embeddings = ops.cat((cls_tokens, embeddings), dim=1)

        # add positional encoding to each token
        if interpolate_pos_encoding:
            embeddings = embeddings + self.interpolate_pos_encoding(embeddings, height, width)
        else:
            embeddings = embeddings + self.position_embeddings

        embeddings = self.dropout(embeddings)

        return embeddings


# Based on timm implementation, which can be found here:
# https://github.com/rwightman/pytorch-image-models/blob/master/timm/models/image_transformer.py
class PatchEmbeddings(nn.Module):
    """
    Image to Patch Embedding.
    """

    def __init__(
        self,
        image_size: int = 224,
        patch_size: Union[int, Tuple[int, int]] = 16,
        num_channels: int = 3,
        embed_dim: int = 768,
    ):
        super().__init__()
        if not isinstance(image_size, collections.abc.Iterable):
            image_size = (image_size, image_size)
        if not isinstance(patch_size, collections.abc.Iterable):
            patch_size = (patch_size, patch_size)
        num_patches = (image_size[1] // patch_size[1]) * (image_size[0] // patch_size[0])
        self.image_size = image_size
        self.patch_size = patch_size
        self.num_patches = num_patches

        self.projection = nn.Conv2d(num_channels, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, pixel_values: mindspore.Tensor, interpolate_pos_encoding: bool = False) -> mindspore.Tensor:
        batch_size, num_channels, height, width = pixel_values.shape
        if not interpolate_pos_encoding:
            if height != self.image_size[0] or width != self.image_size[1]:
                raise ValueError(
                    f"Input image size ({height}*{width}) doesn't match model"
                    f" ({self.image_size[0]}*{self.image_size[1]})."
                )
        x = ops.transpose(ops.flatten(self.projection(pixel_values), 2), 1, 2)
        return x


class FlavaTextEmbeddings(nn.Module):
    """Construct the embeddings from word, position and token_type embeddings."""

    def __init__(self, config):
        super().__init__()
        self.word_embeddings = nn.Embedding(config.vocab_size, config.hidden_size, padding_idx=config.pad_token_id)
        self.position_embeddings = nn.Embedding(config.max_position_embeddings, config.hidden_size)
        self.token_type_embeddings = nn.Embedding(config.type_vocab_size, config.hidden_size)

        # self.LayerNorm is not snake-cased to stick with TensorFlow model variable name and be able to load
        # any TensorFlow checkpoint file
        self.LayerNorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        # position_ids (1, len position emb) is contiguous in memory and exported when serialized
        self.position_embedding_type = getattr(config, "position_embedding_type", "absolute")
        self.register_buffer(
            "position_ids", ops.arange(config.max_position_embeddings).broadcast_to((1, -1)), persistent=False
        )
        self.register_buffer(
            "token_type_ids", ops.zeros(self.position_ids.shape, dtype=mindspore.int64), persistent=False
        )

    def forward(
        self,
        input_ids: Optional[mindspore.Tensor] = None,
        token_type_ids: Optional[mindspore.Tensor] = None,
        position_ids: Optional[mindspore.Tensor] = None,
    ):
        input_shape = input_ids.shape
        seq_length = input_shape[1]

        if position_ids is None:
            position_ids = self.position_ids[:, :seq_length]

        # Setting the token_type_ids to the registered buffer in constructor where it is all zeros, which usually occurs
        # when its auto-generated, registered buffer helps users when tracing the model without passing token_type_ids, solves
        # issue #5664
        if token_type_ids is None:
            if hasattr(self, "token_type_ids"):
                buffered_token_type_ids = self.token_type_ids[:, :seq_length]
                buffered_token_type_ids_expanded = buffered_token_type_ids.broadcast_to((input_shape[0], seq_length))
                token_type_ids = buffered_token_type_ids_expanded
            else:
                token_type_ids = ops.zeros(input_shape, dtype=mindspore.int64)

        inputs_embeds = self.word_embeddings(input_ids)
        token_type_embeddings = self.token_type_embeddings(token_type_ids)

        embeddings = inputs_embeds + token_type_embeddings
        if self.position_embedding_type == "absolute":
            position_embeddings = self.position_embeddings(position_ids)
            embeddings += position_embeddings
        embeddings = self.LayerNorm(embeddings)
        embeddings = self.dropout(embeddings)
        return embeddings


class FlavaSelfAttention(nn.Module):
    def __init__(self, config: FlavaPossibleConfigs) -> None:
        super().__init__()
        if config.hidden_size % config.num_attention_heads != 0 and not hasattr(config, "embedding_size"):
            raise ValueError(
                f"The hidden size {config.hidden_size,} is not a multiple of the number of attention "
                f"heads {config.num_attention_heads}."
            )

        self.num_attention_heads = config.num_attention_heads
        self.attention_head_size = int(config.hidden_size / config.num_attention_heads)
        self.all_head_size = self.num_attention_heads * self.attention_head_size

        self.query = nn.Linear(config.hidden_size, self.all_head_size, bias=config.qkv_bias)
        self.key = nn.Linear(config.hidden_size, self.all_head_size, bias=config.qkv_bias)
        self.value = nn.Linear(config.hidden_size, self.all_head_size, bias=config.qkv_bias)

        self.dropout = nn.Dropout(config.attention_probs_dropout_prob)

    def transpose_for_scores(self, x: mindspore.Tensor) -> mindspore.Tensor:
        new_x_shape = x.shape[:-1] + (self.num_attention_heads, self.attention_head_size)
        x = x.view(*new_x_shape)
        return x.permute(0, 2, 1, 3)

    def forward(
        self,
        hidden_states: mindspore.Tensor,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: bool = False,
    ) -> Union[Tuple[mindspore.Tensor, mindspore.Tensor], Tuple[mindspore.Tensor]]:
        mixed_query_layer = self.query(hidden_states)

        key_layer = self.transpose_for_scores(self.key(hidden_states))
        value_layer = self.transpose_for_scores(self.value(hidden_states))
        query_layer = self.transpose_for_scores(mixed_query_layer)

        # Take the dot product between "query" and "key" to get the raw attention scores.
        attention_scores = ops.matmul(query_layer, ops.transpose(key_layer, -1, -2))

        attention_scores = attention_scores / math.sqrt(self.attention_head_size)
        if attention_mask is not None:
            # Apply the attention mask is (precomputed for all layers in BertModel forward() function)
            attention_scores = attention_scores + attention_mask

        # Normalize the attention scores to probabilities.
        attention_probs = nn.functional.softmax(attention_scores, dim=-1)

        # This is actually dropping out entire tokens to attend to, which might
        # seem a bit unusual, but is taken from the original Transformer paper.
        attention_probs = self.dropout(attention_probs)

        # Mask heads if we want to
        if head_mask is not None:
            attention_probs = attention_probs * head_mask

        context_layer = ops.matmul(attention_probs, value_layer)

        context_layer = context_layer.permute(0, 2, 1, 3)
        new_context_layer_shape = context_layer.shape[:-2] + (self.all_head_size,)
        context_layer = context_layer.view(*new_context_layer_shape)

        outputs = (context_layer, attention_probs) if output_attentions else (context_layer,)

        return outputs


class FlavaSelfOutput(nn.Module):
    """
    The residual connection is defined in FlavaLayer (same as ViTLayer) instead of here (as is the case with other
    models), due to the layernorm applied before each block.
    """

    def __init__(self, config: FlavaPossibleConfigs) -> None:
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    def forward(self, hidden_states: mindspore.Tensor, input_tensor: mindspore.Tensor) -> mindspore.Tensor:
        hidden_states = self.dense(hidden_states)
        hidden_states = self.dropout(hidden_states)

        return hidden_states


class FlavaAttention(nn.Module):
    def __init__(self, config: FlavaPossibleConfigs) -> None:
        super().__init__()
        self.attention = FlavaSelfAttention(config)
        self.output = FlavaSelfOutput(config)
        self.pruned_heads = set()

    def prune_heads(self, heads: Set[int]) -> None:
        if len(heads) == 0:
            return
        heads, index = find_pruneable_heads_and_indices(
            heads, self.attention.num_attention_heads, self.attention.attention_head_size, self.pruned_heads
        )

        # Prune linear layers
        self.attention.query = prune_linear_layer(self.attention.query, index)
        self.attention.key = prune_linear_layer(self.attention.key, index)
        self.attention.value = prune_linear_layer(self.attention.value, index)
        self.output.dense = prune_linear_layer(self.output.dense, index, dim=1)

        # Update hyper params and store pruned heads
        self.attention.num_attention_heads = self.attention.num_attention_heads - len(heads)
        self.attention.all_head_size = self.attention.attention_head_size * self.attention.num_attention_heads
        self.pruned_heads = self.pruned_heads.union(heads)

    def forward(
        self,
        hidden_states: mindspore.Tensor,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: bool = False,
    ) -> Union[Tuple[mindspore.Tensor, mindspore.Tensor], Tuple[mindspore.Tensor]]:
        self_outputs = self.attention(
            hidden_states, attention_mask=attention_mask, head_mask=head_mask, output_attentions=output_attentions
        )

        attention_output = self.output(self_outputs[0], hidden_states)

        outputs = (attention_output,) + self_outputs[1:]  # add attentions if we output them
        return outputs


class FlavaIntermediate(nn.Module):
    def __init__(self, config: FlavaPossibleConfigs) -> None:
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.intermediate_size)
        if isinstance(config.hidden_act, str):
            self.intermediate_act_fn = ACT2FN[config.hidden_act]
        else:
            self.intermediate_act_fn = config.hidden_act

    # Copied from transformers.models.vit.modeling_vit.ViTIntermediate.forward
    def forward(self, hidden_states: mindspore.Tensor) -> mindspore.Tensor:
        hidden_states = self.dense(hidden_states)
        hidden_states = self.intermediate_act_fn(hidden_states)

        return hidden_states


class FlavaOutput(nn.Module):
    def __init__(self, config: FlavaPossibleConfigs) -> None:
        super().__init__()
        self.dense = nn.Linear(config.intermediate_size, config.hidden_size)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)

    # Copied from transformers.models.vit.modeling_vit.ViTOutput.forward
    def forward(self, hidden_states: mindspore.Tensor, input_tensor: mindspore.Tensor) -> mindspore.Tensor:
        hidden_states = self.dense(hidden_states)
        hidden_states = self.dropout(hidden_states)

        hidden_states = hidden_states + input_tensor

        return hidden_states


class FlavaLayer(nn.Module):
    """This corresponds to the Block class in the timm implementation."""

    def __init__(self, config: FlavaPossibleConfigs) -> None:
        super().__init__()
        self.chunk_size_feed_forward = config.chunk_size_feed_forward
        self.seq_len_dim = 1
        self.attention = FlavaAttention(config)
        self.intermediate = FlavaIntermediate(config)
        self.output = FlavaOutput(config)

        # TODO: Check fp32 layer norm possiblity
        self.layernorm_before = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.layernorm_after = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

    def forward(
        self,
        hidden_states: mindspore.Tensor,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: bool = False,
    ) -> Union[Tuple[mindspore.Tensor, mindspore.Tensor], Tuple[mindspore.Tensor]]:
        self_attention_outputs = self.attention(
            self.layernorm_before(hidden_states),  # in ViT, layernorm is applied before self-attention
            attention_mask=attention_mask,
            head_mask=head_mask,
            output_attentions=output_attentions,
        )
        attention_output = self_attention_outputs[0]
        outputs = self_attention_outputs[1:]  # add self attentions if we output attention weights

        # first residual connection
        hidden_states = attention_output + hidden_states

        # in ViT, layernorm is also applied after self-attention
        layer_output = self.layernorm_after(hidden_states)
        layer_output = self.intermediate(layer_output)

        # second residual connection is done here
        layer_output = self.output(layer_output, hidden_states)

        outputs = (layer_output,) + outputs

        return outputs


class FlavaEncoder(nn.Module):
    def __init__(self, config: FlavaConfig) -> None:
        super().__init__()
        self.config = config
        self.layer = nn.ModuleList([FlavaLayer(config) for _ in range(config.num_hidden_layers)])
        self.gradient_checkpointing = False

    def forward(
        self,
        hidden_states: mindspore.Tensor,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: bool = False,
        output_hidden_states: bool = False,
        return_dict: bool = True,
    ) -> Union[tuple, BaseModelOutput]:
        all_hidden_states = () if output_hidden_states else None
        all_self_attentions = () if output_attentions else None

        for i, layer_module in enumerate(self.layer):
            if output_hidden_states:
                all_hidden_states = all_hidden_states + (hidden_states,)

            layer_head_mask = head_mask[i] if head_mask is not None else None

            if self.gradient_checkpointing and self.training:
                layer_outputs = self._gradient_checkpointing_func(
                    layer_module.__call__,
                    hidden_states,
                    attention_mask,
                    layer_head_mask,
                    output_attentions,
                )
            else:
                layer_outputs = layer_module(hidden_states, attention_mask, layer_head_mask, output_attentions)

            hidden_states = layer_outputs[0]

            if output_attentions:
                all_self_attentions = all_self_attentions + (layer_outputs[1],)

        if output_hidden_states:
            all_hidden_states = all_hidden_states + (hidden_states,)

        if not return_dict:
            return tuple(v for v in [hidden_states, all_hidden_states, all_self_attentions] if v is not None)
        return BaseModelOutput(
            last_hidden_state=hidden_states, hidden_states=all_hidden_states, attentions=all_self_attentions
        )


class FlavaPooler(nn.Module):
    def __init__(self, config: FlavaPossibleConfigs):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.activation = nn.Tanh()

    def forward(self, hidden_states: mindspore.Tensor):
        # We "pool" the model by simply taking the hidden state corresponding
        # to the first token.
        first_token_tensor = hidden_states[:, 0]
        pooled_output = self.dense(first_token_tensor)
        pooled_output = self.activation(pooled_output)
        return pooled_output


class FlavaPreTrainedModel(PreTrainedModel):
    """
    An abstract class to handle weights initialization and a simple interface for downloading and loading pretrained
    models.
    """

    config_class = FlavaConfig
    base_model_prefix = "flava"
    supports_gradient_checkpointing = True

    def _init_weights(self, module: Union[nn.Linear, nn.Conv2d, nn.LayerNorm]) -> None:
        """Initialize the weights"""
        if isinstance(module, (nn.Linear, nn.Conv2d)):
            # Slightly different from the TF version which uses truncated_normal for initialization
            # cf https://github.com/pytorch/pytorch/pull/5617
            nn.init.normal_(module.weight, mean=0.0, std=self.config.initializer_range)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=self.config.initializer_range)
            if module.padding_idx is not None:
                module.weight[module.padding_idx] = 0
        elif isinstance(module, nn.LayerNorm):
            nn.init.zeros_(module.bias)
            nn.init.ones_(module.weight)


class FlavaImageModel(FlavaPreTrainedModel):
    config_class = FlavaImageConfig
    # This override allows us to load FlavaImageModel from FlavaModel/FlavaForPreTraining checkpoints.
    base_model_prefix = "flava.image_model"
    main_input_name = "pixel_values"

    def __init__(self, config: FlavaImageConfig, add_pooling_layer: bool = True):
        super().__init__(config)

        self.config = config

        self.embeddings = FlavaImageEmbeddings(config)
        self.encoder = FlavaEncoder(config)

        self.layernorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.pooler = FlavaPooler(config) if add_pooling_layer else None

        self.post_init()

    def get_input_embeddings(self) -> nn.Module:
        return self.embeddings.patch_embeddings

    def set_input_embeddings(self, value: nn.Module):
        self.embeddings.patch_embeddings = value

    def _prune_heads(self, heads_to_prune: Dict[int, List[int]]) -> None:
        """
        Prunes heads of the model. heads_to_prune: dict of {layer_num: list of heads to prune in this layer} See base
        class PreTrainedModel
        """
        for layer, heads in heads_to_prune.items():
            self.encoder.layer[layer].attention.prune_heads(heads)

    def forward(
        self,
        pixel_values: Optional[mindspore.Tensor] = None,
        bool_masked_pos: Optional[mindspore.Tensor] = None,
        interpolate_pos_encoding: Optional[bool] = None,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[tuple, BaseModelOutputWithPooling]:
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if pixel_values is None:
            raise ValueError("You have to specify pixel_values")

        # Prepare head mask if needed
        # 1.0 in head_mask indicate we keep the head
        # attention_probs has shape bsz x n_heads x N x N
        # input head_mask has shape [num_heads] or [num_hidden_layers x num_heads]
        # and head_mask is converted to shape [num_hidden_layers x batch x num_heads x seq_length x seq_length]
        head_mask = self.get_head_mask(head_mask, self.config.num_hidden_layers)

        embedding_output = self.embeddings(
            pixel_values, bool_masked_pos=bool_masked_pos, interpolate_pos_encoding=interpolate_pos_encoding
        )

        encoder_outputs = self.encoder(
            embedding_output,
            attention_mask=attention_mask,
            head_mask=head_mask,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = encoder_outputs[0]
        sequence_output = self.layernorm(sequence_output)
        pooled_output = self.pooler(sequence_output) if self.pooler is not None else None

        if not return_dict:
            return (sequence_output, pooled_output) + encoder_outputs[1:]

        return BaseModelOutputWithPooling(
            last_hidden_state=sequence_output,
            pooler_output=pooled_output,
            hidden_states=encoder_outputs.hidden_states,
            attentions=encoder_outputs.attentions,
        )


class FlavaTextModel(FlavaPreTrainedModel):
    config_class = FlavaTextConfig
    # This override allows us to load FlavaTextModel from FlavaModel/FlavaForPreTraining checkpoints.
    base_model_prefix = "flava.text_model"

    def __init__(self, config: FlavaTextConfig, add_pooling_layer: bool = True):
        super().__init__(config)
        self.config = config

        self.embeddings = FlavaTextEmbeddings(config)
        self.encoder = FlavaEncoder(config)

        self.layernorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.pooler = FlavaPooler(config) if add_pooling_layer else None

        self.post_init()

    def get_input_embeddings(self) -> PatchEmbeddings:
        return self.embeddings.word_embeddings

    def set_input_embeddings(self, value: nn.Module):
        self.embeddings.word_embeddings = value

    def _prune_heads(self, heads_to_prune: Dict[int, List[int]]) -> None:
        """
        Prunes heads of the model. heads_to_prune: dict of {layer_num: list of heads to prune in this layer} See base
        class PreTrainedModel
        """
        for layer, heads in heads_to_prune.items():
            self.encoder.layer[layer].attention.prune_heads(heads)

    def forward(
        self,
        input_ids: Optional[mindspore.Tensor] = None,
        attention_mask: Optional[mindspore.Tensor] = None,
        token_type_ids: Optional[mindspore.Tensor] = None,
        position_ids: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[tuple, BaseModelOutputWithPooling]:
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        if input_ids is None:
            raise ValueError("You have to specify input_ids")

        input_shape = input_ids.shape

        if attention_mask is None:
            attention_mask = ops.ones(input_shape)

        # Prepare head mask if needed
        # 1.0 in head_mask indicate we keep the head
        # attention_probs has shape bsz x n_heads x N x N
        # input head_mask has shape [num_heads] or [num_hidden_layers x num_heads]
        # and head_mask is converted to shape [num_hidden_layers x batch x num_heads x seq_length x seq_length]
        head_mask = self.get_head_mask(head_mask, self.config.num_hidden_layers)
        extended_attention_mask: mindspore.Tensor = self.get_extended_attention_mask(
            attention_mask, input_shape
        )

        embedding_output = self.embeddings(
            input_ids=input_ids,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
        )

        encoder_outputs = self.encoder(
            embedding_output,
            attention_mask=extended_attention_mask,
            head_mask=head_mask,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = encoder_outputs[0]
        sequence_output = self.layernorm(sequence_output)
        pooled_output = self.pooler(sequence_output) if self.pooler is not None else None

        if not return_dict:
            return (sequence_output, pooled_output) + encoder_outputs[1:]

        return BaseModelOutputWithPooling(
            last_hidden_state=sequence_output,
            pooler_output=pooled_output,
            hidden_states=encoder_outputs.hidden_states,
            attentions=encoder_outputs.attentions,
        )


class FlavaMultimodalModel(FlavaPreTrainedModel):
    config_class = FlavaMultimodalConfig
    # This override allows us to load FlavaMultimodalModel from FlavaModel/FlavaForPreTraining checkpoints.
    base_model_prefix = "flava.multimodal_model"
    main_input_name = "hidden_states"

    def __init__(self, config: FlavaMultimodalConfig, add_pooling_layer=True):
        super().__init__(config)
        self.config = config
        self.use_cls_token = self.config.use_cls_token
        if self.use_cls_token:
            self.cls_token = nn.Parameter(ops.zeros(1, 1, config.hidden_size))

        self.encoder = FlavaEncoder(config)

        self.layernorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)
        self.pooler = FlavaPooler(config) if add_pooling_layer else None

        self.post_init()

    def _prune_heads(self, heads_to_prune: Dict[int, List[int]]) -> None:
        """
        Prunes heads of the model. heads_to_prune: dict of {layer_num: list of heads to prune in this layer} See base
        class PreTrainedModel
        """
        for layer, heads in heads_to_prune.items():
            self.encoder.layer[layer].attention.prune_heads(heads)

    def forward(
        self,
        hidden_states: mindspore.Tensor,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[tuple, BaseModelOutputWithPooling]:
        output_attentions = output_attentions if output_attentions is not None else self.config.output_attentions
        output_hidden_states = (
            output_hidden_states if output_hidden_states is not None else self.config.output_hidden_states
        )
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        batch_size, seq_length, _ = hidden_states.shape

        if self.use_cls_token:
            cls_tokens = self.cls_token.broadcast_to((batch_size, -1, -1))
            hidden_states = ops.cat((cls_tokens, hidden_states), dim=1)
            seq_length += 1

        if attention_mask is None:
            attention_mask = ops.ones((batch_size, seq_length))

        # Prepare head mask if needed
        # 1.0 in head_mask indicate we keep the head
        # attention_probs has shape bsz x n_heads x N x N
        # input head_mask has shape [num_heads] or [num_hidden_layers x num_heads]
        # and head_mask is converted to shape [num_hidden_layers x batch x num_heads x seq_length x seq_length]
        head_mask = self.get_head_mask(head_mask, self.config.num_hidden_layers)
        extended_attention_mask: mindspore.Tensor = self.get_extended_attention_mask(
            attention_mask, (batch_size, seq_length)
        )

        encoder_outputs = self.encoder(
            hidden_states,
            attention_mask=extended_attention_mask,
            head_mask=head_mask,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        sequence_output = encoder_outputs[0]
        sequence_output = self.layernorm(sequence_output)
        pooled_output = self.pooler(sequence_output) if self.pooler is not None else None

        if not return_dict:
            return (sequence_output, pooled_output) + encoder_outputs[1:]

        return BaseModelOutputWithPooling(
            last_hidden_state=sequence_output,
            pooler_output=pooled_output,
            hidden_states=encoder_outputs.hidden_states,
            attentions=encoder_outputs.attentions,
        )


class FlavaModel(FlavaPreTrainedModel):
    config_class = FlavaConfig

    def __init__(self, config: FlavaConfig):
        super().__init__(config)

        if not isinstance(config.text_config, FlavaTextConfig):
            raise TypeError(
                "config.text_config is expected to be of type FlavaTextConfig but is of type"
                f" {type(config.text_config)}."
            )

        if not isinstance(config.image_config, FlavaImageConfig):
            raise TypeError(
                "config.image_config is expected to be of type FlavaImageConfig but is of type"
                f" {type(config.image_config)}."
            )

        if not isinstance(config.multimodal_config, FlavaMultimodalConfig):
            raise TypeError(
                "config.multimodal_config is expected to be of type FlavaMultimodalConfig but "
                + f"is of type {type(config.multimodal_config)}."
            )

        text_config = config.text_config
        image_config = config.image_config
        multimodal_config = config.multimodal_config

        self.projection_dim = config.projection_dim
        self.text_hidden_size = text_config.hidden_size
        self.image_hidden_size = image_config.hidden_size
        self.mm_hidden_size = multimodal_config.hidden_size

        self.text_model = FlavaTextModel(text_config)
        self.image_model = FlavaImageModel(image_config)
        self.multimodal_model = FlavaMultimodalModel(multimodal_config)

        self.image_projection = nn.Linear(self.image_hidden_size, self.projection_dim)
        self.text_projection = nn.Linear(self.text_hidden_size, self.projection_dim)
        self.logit_scale = nn.Parameter(mindspore.tensor(self.config.logit_scale_init_value))

        self.image_to_mm_projection = nn.Linear(self.image_hidden_size, self.mm_hidden_size)
        self.text_to_mm_projection = nn.Linear(self.text_hidden_size, self.mm_hidden_size)
        # Initialize weights and apply final processing
        self.post_init()

    def get_text_features(
        self,
        input_ids: Optional[mindspore.Tensor] = None,
        attention_mask: Optional[mindspore.Tensor] = None,
        token_type_ids: Optional[mindspore.Tensor] = None,
        position_ids: Optional[mindspore.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> mindspore.Tensor:
        r"""
        Returns:
            text_features (`mindspore.Tensor` of shape `(batch_size, output_dim`): The text embeddings obtained by
            applying the projection layer to the pooled output of [`FlavaTextModel`].

        Examples:

        ```python
        >>> from transformers import AutoProcessor, FlavaModel

        >>> model = FlavaModel.from_pretrained("{0}")
        >>> processor = AutoProcessor.from_pretrained("{0}")

        >>> inputs = processor(
        ...     text=["a photo of a cat", "a photo of a dog"], max_length=77, padding="max_length", return_tensors="ms"
        ... )
        >>> text_features = model.get_text_features(**inputs)
        ```""".format(_CHECKPOINT_FOR_DOC)
        text_outputs = self.text_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        pooled_output = text_outputs[0]  # last_hidden_state
        text_features = self.text_projection(pooled_output)

        return text_features

    def get_image_features(
        self,
        pixel_values: Optional[mindspore.Tensor] = None,
        bool_masked_pos: Optional[mindspore.Tensor] = None,
        interpolate_pos_encoding: Optional[bool] = None,
        attention_mask: Optional[mindspore.Tensor] = None,
        head_mask: Optional[mindspore.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> mindspore.Tensor:
        r"""
        Returns:
            image_features (`mindspore.Tensor` of shape `(batch_size, output_dim`): The image embeddings obtained by
            applying the projection layer to the pooled output of [`FlavaImageModel`].

        Examples:

        ```python
        >>> from PIL import Image
        >>> import requests
        >>> from transformers import AutoProcessor, FlavaModel

        >>> model = FlavaModel.from_pretrained("{0}")
        >>> processor = AutoProcessor.from_pretrained("{0}")

        >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
        >>> image = Image.open(requests.get(url, stream=True).raw)

        >>> inputs = processor(images=image, return_tensors="ms")

        >>> image_features = model.get_image_features(**inputs)
        ```""".format(_CHECKPOINT_FOR_DOC)
        image_outputs = self.image_model(
            pixel_values=pixel_values,
            bool_masked_pos=bool_masked_pos,
            attention_mask=attention_mask,
            head_mask=head_mask,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            interpolate_pos_encoding=interpolate_pos_encoding,
            return_dict=return_dict,
        )

        pooled_output = image_outputs[0]  # last_hidden_state
        image_features = self.image_projection(pooled_output)

        return image_features

    def forward(
        self,
        input_ids: Optional[mindspore.Tensor] = None,
        pixel_values: Optional[mindspore.Tensor] = None,
        attention_mask: Optional[mindspore.Tensor] = None,
        token_type_ids: Optional[mindspore.Tensor] = None,
        bool_masked_pos: Optional[mindspore.Tensor] = None,
        position_ids: Optional[mindspore.Tensor] = None,
        image_attention_mask: Optional[mindspore.Tensor] = None,
        skip_multimodal_encoder: Optional[bool] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: bool = True,
        return_dict: Optional[bool] = None,
    ) -> Union[Tuple, FlavaOutput]:
        r"""
        Returns:

        Examples:

        ```python
        >>> from PIL import Image
        >>> import requests
        >>> from transformers import AutoProcessor, FlavaModel

        >>> model = FlavaModel.from_pretrained("facebook/flava-full")
        >>> processor = AutoProcessor.from_pretrained("facebook/flava-full")

        >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
        >>> image = Image.open(requests.get(url, stream=True).raw)

        >>> inputs = processor(text=["a photo of a cat"], images=image, return_tensors="ms", padding=True)

        >>> outputs = model(**inputs)

        >>> image_embeddings = outputs.image_embeddings
        >>> text_embeddings = outputs.text_embeddings
        >>> multimodal_embeddings = outputs.multimodal_embeddings

        >>> outputs.image_embeddings.shape

        >>> text_embeddings.shape

        >>> multimodal_embeddings.shape
        ```
        """

        return_dict = return_dict if return_dict is not None else self.config.return_dict
        if not output_hidden_states:
            raise ValueError("FLAVA model requires hidden states to work. Please set `output_hidden_states=True`")
        image_embeddings = None
        image_states = None
        image_mm_projection = None
        image_output = None
        if pixel_values is not None:
            image_output = self.image_model(
                pixel_values=pixel_values,
                bool_masked_pos=bool_masked_pos,
                attention_mask=image_attention_mask,
                output_attentions=output_attentions,
                output_hidden_states=output_hidden_states,
                return_dict=return_dict,
            )
            image_embeddings, image_states = image_output[0], image_output[2]
            # Note that these states don't use final layernorm in the transformer model
            image_mm_projection = self.image_to_mm_projection(image_states[-1])

        text_embeddings = None
        text_states = None
        text_mm_projection = None
        text_output = None
        if input_ids is not None:
            text_output = self.text_model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                position_ids=position_ids,
                token_type_ids=token_type_ids,
                output_attentions=output_attentions,
                output_hidden_states=output_hidden_states,
                return_dict=return_dict,
            )

            text_embeddings, text_states = text_output[0], text_output[2]
            # Note that these states don't use final layernorm in the transformer model
            text_mm_projection = self.text_to_mm_projection(text_states[-1])

        multimodal_embeddings = None
        multimodal_output = None
        if image_mm_projection is not None and text_mm_projection is not None and not skip_multimodal_encoder:
            if attention_mask is not None:
                batch_size, seq_len, _ = image_mm_projection.shape
                if self.multimodal_model.use_cls_token:
                    seq_len += 1
                attention_mask_image = ops.ones(batch_size, seq_len, dtype=attention_mask.dtype)
                attention_multimodal = ops.cat([attention_mask_image, attention_mask], dim=1)
            else:
                attention_multimodal = None
            multimodal_input = ops.cat([image_mm_projection, text_mm_projection], dim=1)
            multimodal_output = self.multimodal_model(
                multimodal_input, attention_mask=attention_multimodal, return_dict=return_dict
            )
            multimodal_embeddings = multimodal_output[0]

        if not return_dict:
            return (
                image_embeddings,
                image_output,
                text_embeddings,
                text_output,
                multimodal_embeddings,
                multimodal_output,
            )

        return FlavaModelOutput(
            image_embeddings=image_embeddings,
            image_output=image_output,
            text_embeddings=text_embeddings,
            text_output=text_output,
            multimodal_embeddings=multimodal_embeddings,
            multimodal_output=multimodal_output,
        )


class FlavaImageCodebookResPath(nn.Module):
    def __init__(self, in_size: int, out_size: int, **kwargs):
        super().__init__()
        hid_size = out_size // 4

        path = OrderedDict()
        path["relu_1"] = nn.ReLU()
        path["conv_1"] = nn.Conv2d(in_size, hid_size, kernel_size=3, padding=1)
        path["relu_2"] = nn.ReLU()
        path["conv_2"] = nn.Conv2d(hid_size, hid_size, kernel_size=3, padding=1)
        path["relu_3"] = nn.ReLU()
        path["conv_3"] = nn.Conv2d(hid_size, hid_size, kernel_size=3, padding=1)
        path["relu_4"] = nn.ReLU()
        path["conv_4"] = nn.Conv2d(hid_size, out_size, kernel_size=1, padding=0)

        self.path = nn.Sequential(path)

    def forward(self, x: mindspore.Tensor) -> mindspore.Tensor:
        return self.path(x)


class FlavaImageCodebookBlock(nn.Module):
    def __init__(self, in_size: int, out_size: int, num_layers: int, **kwargs):
        super().__init__()

        self.post_gain = 1 / (num_layers**2)

        if in_size != out_size:
            self.id_path = nn.Conv2d(in_size, out_size, kernel_size=1, padding=0)
        else:
            self.id_path = nn.Identity()

        self.res_path = FlavaImageCodebookResPath(in_size, out_size)

    def forward(self, x: mindspore.Tensor) -> mindspore.Tensor:
        return self.id_path(x) + self.post_gain * self.res_path(x)


class FlavaImageCodebookLayerGroup(nn.Module):
    def __init__(self, num_blocks: int, num_layers: int, in_size: int, out_size: int, use_pool: bool = True):
        super().__init__()
        blocks = OrderedDict()
        for i in range(num_blocks):
            if i == 0:
                blocks[f"block_{i+1}"] = FlavaImageCodebookBlock(in_size, out_size, num_layers)
            else:
                blocks[f"block_{i+1}"] = FlavaImageCodebookBlock(out_size, out_size, num_layers)

        if use_pool:
            blocks["pool"] = nn.MaxPool2d(kernel_size=2)

        self.group = nn.Sequential(blocks)

    def forward(self, x: mindspore.Tensor) -> mindspore.Tensor:
        return self.group(x)


class FlavaImageCodebook(FlavaPreTrainedModel):
    base_model_prefix = ""
    config_class = FlavaImageCodebookConfig
    main_input_name = "pixel_values"
    supports_gradient_checkpointing = False

    def __init__(
        self,
        config: FlavaImageCodebookConfig,
        **kwargs: Any,
    ):
        super().__init__(config)

        self.config = config
        self.num_groups = config.num_groups
        self.input_channels = config.input_channels
        self.num_blocks_per_group = config.num_blocks_per_group
        self.hidden_size = config.hidden_size
        self.vocab_size = config.vocab_size

        num_layers = self.num_groups * self.num_blocks_per_group

        output_blocks = OrderedDict()
        output_blocks["relu"] = nn.ReLU()
        output_blocks["conv"] = nn.Conv2d(8 * self.hidden_size, self.vocab_size, kernel_size=1, padding=0)

        blocks = OrderedDict()
        blocks["input"] = nn.Conv2d(self.input_channels, 1 * self.hidden_size, kernel_size=7, padding=3)
        blocks["group_1"] = FlavaImageCodebookLayerGroup(
            self.num_blocks_per_group, num_layers, 1 * self.hidden_size, 1 * self.hidden_size
        )
        blocks["group_2"] = FlavaImageCodebookLayerGroup(
            self.num_blocks_per_group, num_layers, 1 * self.hidden_size, 2 * self.hidden_size
        )
        blocks["group_3"] = FlavaImageCodebookLayerGroup(
            self.num_blocks_per_group, num_layers, 2 * self.hidden_size, 4 * self.hidden_size
        )
        blocks["group_4"] = FlavaImageCodebookLayerGroup(
            self.num_blocks_per_group, num_layers, 4 * self.hidden_size, 8 * self.hidden_size, use_pool=False
        )
        blocks["output"] = nn.Sequential(output_blocks)

        self.blocks = nn.Sequential(blocks)

        self.post_init()

        if self.config.freeze:
            for param in self.parameters():
                param.requires_grad = False

    def get_codebook_indices(self, pixel_values: mindspore.Tensor) -> mindspore.Tensor:
        """
        Args:
            pixel_values (`mindspore.Tensor` of shape `(batch_size, num_channels, height, width)`):
                Pixel values. Codebook pixel values can be obtained using [`AutoImageProcessor`] by passing
                `return_codebook_pixels=True`. See [`FlavaImageProcessor.__call__`] for details.

        Examples:
        ```python
        >>> from PIL import Image
        >>> import requests
        >>> from transformers import AutoImageProcessor, FlavaImageCodebook

        >>> model = FlavaImageCodebook.from_pretrained("{0}")
        >>> image_processor = AutoImageProcessor.from_pretrained("{0}")

        >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
        >>> image = Image.open(requests.get(url, stream=True).raw)

        >>> inputs = image_processor([image], return_codebook_pixels=True, return_tensors="ms")
        >>> inputs = dict(pixel_values=inputs.codebook_pixel_values)

        >>> outputs = model.get_codebook_indices(**inputs)
        ```
        """.format(_CHECKPOINT_FOR_CODEBOOK_DOC)
        z_logits = self.blocks(pixel_values)
        return ops.argmax(z_logits, dim=1)

    def get_codebook_probs(self, pixel_values: mindspore.Tensor) -> mindspore.Tensor:
        z_logits = self.blocks(pixel_values)
        return nn.Softmax(dim=1)(z_logits)

    def forward(self, pixel_values: mindspore.Tensor) -> mindspore.Tensor:
        """
        Args:
            pixel_values (`mindspore.Tensor` of shape `(batch_size, num_channels, height, width)`):
                Pixel values. Codebook pixel values can be obtained using [`AutoImageProcessor`] by passing
                `return_codebook_pixels=True`. See [`FlavaImageProcessor.__call__`] for details.

        Examples:

        ```python
        >>> from PIL import Image
        >>> import requests
        >>> from transformers import AutoImageProcessor, FlavaImageCodebook

        >>> model = FlavaImageCodebook.from_pretrained("{0}")
        >>> image_processor = AutoImageProcessor.from_pretrained("{0}")

        >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
        >>> image = Image.open(requests.get(url, stream=True).raw)

        >>> inputs = image_processor([image], return_codebook_pixels=True, return_tensors="ms")
        >>> inputs = dict(pixel_values=inputs.codebook_pixel_values)

        >>> outputs = model(**inputs)
        >>> print(outputs.shape)
        (1, 196)
        ```
        """.format(_CHECKPOINT_FOR_CODEBOOK_DOC)
        if len(pixel_values.shape) != 4:
            raise ValueError(f"input shape {pixel_values.shape} is not 4d")
        if pixel_values.shape[1] != self.input_channels:
            raise ValueError(f"input has {pixel_values.shape[1]} channels but model built for {self.input_channels}")
        return self.blocks(pixel_values)


class FlavaPredictionHeadTransform(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        if isinstance(config.hidden_act, str):
            self.transform_act_fn = ACT2FN[config.hidden_act]
        else:
            self.transform_act_fn = config.hidden_act
        self.LayerNorm = nn.LayerNorm(config.hidden_size, eps=config.layer_norm_eps)

    def forward(self, hidden_states):
        hidden_states = self.dense(hidden_states)
        hidden_states = self.transform_act_fn(hidden_states)
        hidden_states = self.LayerNorm(hidden_states)
        return hidden_states


class FlavaMaskedPredictionHead(nn.Module):
    def __init__(self, config, weight=None):
        super().__init__()
        self.config = config
        self.transform = FlavaPredictionHeadTransform(config)
        self.decoder = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        self.bias = nn.Parameter(ops.zeros(config.vocab_size))
        if weight is not None:
            self.decoder.weight = weight

        # Need a link between the two variables so that the bias is correctly resized with `resize_token_embeddings`
        self.decoder.bias = self.bias

    def _tie_weights(self):
        self.decoder.bias = self.bias

    def forward(self, x):
        x = self.transform(x)
        x = self.decoder(x)
        return x


class FlavaITMHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.pooler = FlavaPooler(config)
        self.seq_relationship = nn.Linear(config.hidden_size, 2)

    def forward(self, x):
        x = self.pooler(x)
        x = self.seq_relationship(x)
        return x


class FlavaGlobalContrastiveHead(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.global_backprop_contrastive = config.global_backprop_contrastive

    def forward(self, image_embeddings, text_embeddings, logit_scale):
        temperature = ops.exp(logit_scale)
        labels = ops.arange(image_embeddings.shape[0])
        image_embeddings_all = [image_embeddings]
        text_embeddings_all = [text_embeddings]

        image_embeddings_all = ops.cat(image_embeddings_all)
        text_embeddings_all = ops.cat(text_embeddings_all)

        logits_per_image = ops.matmul(image_embeddings, ops.transpose(text_embeddings_all, 0, 1)) * temperature
        logits_per_text = ops.matmul(text_embeddings, ops.transpose(image_embeddings_all, 0, 1)) * temperature

        return logits_per_image, logits_per_text, labels


class FlavaForPreTraining(FlavaPreTrainedModel):
    # Those are linked to xxx.bias
    _tied_weights_keys = [
        "mmm_text_head.decoder.bias",
        "mmm_image_head.decoder.bias",
        "mlm_head.decoder.bias",
        "mim_head.decoder.bias",
    ]

    def __init__(self, config: FlavaConfig, image_codebook: Optional[nn.Module] = None):
        super().__init__(config)
        self.flava = FlavaModel(config)

        self.image_codebook = image_codebook
        if self.image_codebook is None and config.init_codebook:
            self.image_codebook = FlavaImageCodebook(config.image_codebook_config)

        # Levarage text and image encoder configs to create the masked
        # head since it has the right vocab
        self.mim_head = FlavaMaskedPredictionHead(config.image_config)
        self.mlm_head = FlavaMaskedPredictionHead(config.text_config)
        self.itm_head = FlavaITMHead(config)
        self.mmm_image_head = FlavaMaskedPredictionHead(config.image_config)
        self.mmm_text_head = FlavaMaskedPredictionHead(config.text_config)
        self.global_contrastive_head = FlavaGlobalContrastiveHead(config)

        self.image_vocab_size = config.image_config.vocab_size
        self.text_vocab_size = config.text_config.vocab_size
        self.mlm_weight = config.mlm_weight
        self.mim_weight = config.mim_weight
        self.global_contrastive_weight = config.global_contrastive_weight
        self.ce_ignore_index = config.ce_ignore_index
        self.itm_weight = config.itm_weight
        self.mmm_image_weight = config.mmm_image_weight
        self.mmm_text_weight = config.mmm_text_weight
        self.skip_unmasked_multimodal_encoder = config.skip_unmasked_multimodal_encoder

        self.post_init()

    def _resize_to_2d(self, x: mindspore.Tensor):
        if x.dim() > 2:
            x = x.view(x.shape[0], -1)
        return x

    def forward(
        self,
        input_ids: Optional[mindspore.Tensor] = None,
        input_ids_masked: Optional[mindspore.Tensor] = None,
        pixel_values: Optional[mindspore.Tensor] = None,
        codebook_pixel_values: Optional[mindspore.Tensor] = None,
        attention_mask: Optional[mindspore.Tensor] = None,
        token_type_ids: Optional[mindspore.Tensor] = None,
        bool_masked_pos: Optional[mindspore.Tensor] = None,
        position_ids: Optional[mindspore.Tensor] = None,
        image_attention_mask: Optional[mindspore.Tensor] = None,
        skip_unmasked_multimodal_encoder: bool = None,
        mlm_labels: Optional[mindspore.Tensor] = None,
        mim_labels: Optional[mindspore.Tensor] = None,
        itm_labels: Optional[mindspore.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: bool = True,
        return_dict: Optional[bool] = None,
        return_loss: Optional[bool] = None,
    ) -> Union[Tuple[mindspore.Tensor], FlavaForPreTrainingOutput]:
        """
        Examples:
        ```python
        >>> from PIL import Image
        >>> import requests
        >>> from transformers import FlavaForPreTraining, AutoProcessor

        >>> url = "http://images.cocodataset.org/val2017/000000039769.jpg"
        >>> image = Image.open(requests.get(url, stream=True).raw)

        >>> model = FlavaForPreTraining.from_pretrained("facebook/flava-full")
        >>> processor = AutoProcessor.from_pretrained("facebook/flava-full")

        >>> text = ["a photo of a cat"]

        >>> inputs = processor(
        ...     images=[image],
        ...     text=text,
        ...     return_masks=True,
        ...     return_codebook_pixels=True,
        ...     padding=True,
        ...     max_length=77,
        ...     return_tensors="ms",
        ... )


        >>> output = model(**inputs)
        ```

        Return:

        """
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict
        return_loss = return_loss if return_loss is not None else self.config.return_loss

        skip_unmasked_multimodal_encoder = (
            skip_unmasked_multimodal_encoder
            if skip_unmasked_multimodal_encoder is not None
            else self.skip_unmasked_multimodal_encoder
        )

        if input_ids_masked is None and input_ids is not None:
            logger.warning(
                "`input_ids_masked` isn't passed which means MLM loss won't be calculated correctlySetting it to"
                " `input_ids` so that model can work. Please pass it if this is unintentional. This is usually OKAY if"
                " you are doing inference on unmasked text..."
            )
            input_ids_masked = input_ids

        flava_output = self.flava(
            input_ids=input_ids,
            pixel_values=pixel_values,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            image_attention_mask=image_attention_mask,
            # Don't need unmasked multimodal embedding for anything so skip it
            # NOTE: ITM uses masked version
            skip_multimodal_encoder=skip_unmasked_multimodal_encoder,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            # Pass true to have deterministic outputs
            return_dict=True,
        )

        flava_masked_output = self.flava(
            input_ids=input_ids_masked,
            pixel_values=pixel_values,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            image_attention_mask=image_attention_mask,
            bool_masked_pos=bool_masked_pos,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=True,
        )

        pos_mask = None

        image_embeddings = flava_output.image_embeddings
        text_embeddings = flava_output.text_embeddings
        image_masked_embeddings = flava_masked_output.image_embeddings
        text_masked_embeddings = flava_masked_output.text_embeddings
        multimodal_masked_embeddings = flava_masked_output.multimodal_embeddings

        total_loss = mim_loss = mlm_loss = mmm_text_loss = mmm_image_loss = gc_loss = itm_loss = None
        mim_logits = mlm_logits = mmm_text_logits = mmm_image_logits = None
        itm_logits = logits_per_image = logits_per_text = None

        # Calculate mim_labels if necessary from the image_codebook
        if image_masked_embeddings is not None or multimodal_masked_embeddings is not None:
            if mim_labels is None and return_loss:
                if self.image_codebook is None:
                    raise RuntimeError(
                        "`return_loss` is set to True but the image codebook is not initialized and no `mim_labels` "
                        " have been passed. Reinstantiate the model with `init_codebook` set to True or "
                        "pass in your custom `mim_labels`"
                    )
                if codebook_pixel_values is None:
                    raise ValueError(
                        "`codebook_pixel_value` are required to generate `mim_labels` if loss is expected. "
                        "Call `AutoProcessor` with `return_codebook_pixels` set to True"
                    )
                mim_labels = self.image_codebook.get_codebook_indices(codebook_pixel_values)
        # Unimodal MIM Loss
        # If multimodal embeddings are present, we will calculate MMM loss
        if self.mim_weight > 0 and image_masked_embeddings is not None and multimodal_masked_embeddings is None:
            sequence_for_image = image_masked_embeddings

            if mim_labels is not None:
                mim_labels = self._resize_to_2d(mim_labels)
                bool_masked_pos = self._resize_to_2d(bool_masked_pos)
                mim_labels[bool_masked_pos.ne(True)] = self.ce_ignore_index

                sequence_for_image = sequence_for_image[:, -mim_labels.shape[1] :, :]
                masked_tokens = mim_labels.ne(self.ce_ignore_index)
                mim_labels_filtered = mim_labels[masked_tokens]
                sequence_for_image = sequence_for_image[masked_tokens]
                mim_logits = self.mim_head(sequence_for_image)
                if return_loss:
                    mim_loss = nn.functional.cross_entropy(
                        mim_logits.view(-1, self.image_vocab_size), mim_labels_filtered.view(-1)
                    )
                    mim_loss *= self.mim_weight
            else:
                mim_logits = self.mim_head(sequence_for_image)

        # Unimodal MLM Loss
        if self.mlm_weight > 0 and text_masked_embeddings is not None and multimodal_masked_embeddings is None:
            sequence_for_text = text_masked_embeddings
            if mlm_labels is not None:
                mlm_labels = self._resize_to_2d(mlm_labels)
                sequence_for_text = sequence_for_text[:, -mlm_labels.shape[1] :, :]
                masked_tokens = mlm_labels.ne(self.ce_ignore_index)
                mlm_labels_filtered = mlm_labels[masked_tokens]
                sequence_for_text = sequence_for_text[masked_tokens]
                mlm_logits = self.mlm_head(sequence_for_text)
                if return_loss:
                    mlm_loss = nn.functional.cross_entropy(
                        mlm_logits.view(-1, self.text_vocab_size), mlm_labels_filtered.view(-1)
                    )
                    mlm_loss *= self.mlm_weight
            else:
                mlm_logits = self.mlm_head(sequence_for_text)

        # ITM Loss
        if self.itm_weight > 0 and multimodal_masked_embeddings is not None:
            itm_logits = self.itm_head(multimodal_masked_embeddings)

            if itm_labels is not None:
                pos_pairs = itm_labels.ne(0)
                pos_mask = ops.where(pos_pairs.any(), pos_pairs, mindspore.tensor([True], pos_pairs.dtype))
                if return_loss:
                    itm_loss = nn.functional.cross_entropy(itm_logits, itm_labels)
                    itm_loss *= self.itm_weight

                if multimodal_masked_embeddings is not None:
                    multimodal_masked_embeddings = multimodal_masked_embeddings[pos_mask]

                if mlm_labels is not None:
                    mlm_labels = mlm_labels[pos_mask]

                if mim_labels is not None:
                    mim_labels = mim_labels[pos_mask]
                    bool_masked_pos = bool_masked_pos[pos_mask]

        # MMM Image Loss
        if multimodal_masked_embeddings is not None and self.mmm_image_weight > 0:
            sequence_for_image = multimodal_masked_embeddings
            end_index = image_masked_embeddings.shape[1] - 1
            sequence_for_image = sequence_for_image[:, 2 : 2 + end_index, :]

            if mim_labels is not None:
                mim_labels = self._resize_to_2d(mim_labels)
                bool_masked_pos = self._resize_to_2d(bool_masked_pos)
                mim_labels[bool_masked_pos.ne(True)] = self.ce_ignore_index

                masked_tokens = mim_labels.ne(self.ce_ignore_index)
                mim_labels_filtered = mim_labels[masked_tokens]
                sequence_for_image = sequence_for_image[masked_tokens]
                mmm_image_logits = self.mmm_image_head(sequence_for_image)
                if return_loss:
                    mmm_image_loss = nn.functional.cross_entropy(
                        mmm_image_logits.view(-1, self.image_vocab_size), mim_labels_filtered.view(-1)
                    )
                    mmm_image_loss *= self.mmm_image_weight
            else:
                mmm_image_logits = self.mmm_image_head(sequence_for_image)

        # MMM Text Loss
        if multimodal_masked_embeddings is not None and self.mmm_text_weight > 0:
            sequence_for_text = multimodal_masked_embeddings
            sequence_for_text = sequence_for_text[:, -text_masked_embeddings.shape[1] :, :]

            if mlm_labels is not None:
                mlm_labels = self._resize_to_2d(mlm_labels)
                masked_tokens = mlm_labels.ne(self.ce_ignore_index)
                mlm_labels_filtered = mlm_labels[masked_tokens]
                sequence_for_text = sequence_for_text[masked_tokens]
                mmm_text_logits = self.mmm_text_head(sequence_for_text)
                if return_loss:
                    mmm_text_loss = nn.functional.cross_entropy(
                        mmm_text_logits.view(-1, self.text_vocab_size), mlm_labels_filtered.view(-1)
                    )
                    mmm_text_loss *= self.mmm_text_weight
            else:
                mmm_text_logits = self.mmm_text_head(sequence_for_text)

        # Global Contrastive Loss
        if image_embeddings is not None and text_embeddings is not None and self.global_contrastive_weight > 0:
            text_embedding = self.flava.text_projection(text_embeddings[:, 0, :])
            text_embedding = nn.functional.normalize(text_embedding, dim=-1)

            image_embedding = self.flava.image_projection(image_embeddings[:, 0, :])
            image_embedding = nn.functional.normalize(image_embedding, dim=-1)

            ops.assign(self.flava.logit_scale, self.flava.logit_scale.clamp(LOGIT_SCALE_CLAMP_MIN, LOGIT_SCALE_CLAMP_MAX))

            logits_per_image, logits_per_text, gc_labels = self.global_contrastive_head(
                image_embedding, text_embedding, self.flava.logit_scale
            )

            # Apply ITM negative mask if any
            if pos_mask is not None:
                logits_per_image = logits_per_image[pos_mask]
                logits_per_text = logits_per_text[pos_mask]
                gc_labels = gc_labels[pos_mask]

            if return_loss:
                gc_loss_image = nn.functional.cross_entropy(logits_per_image, gc_labels)
                gc_loss_text = nn.functional.cross_entropy(logits_per_text, gc_labels)
                gc_loss = (gc_loss_image + gc_loss_text) / 2
                gc_loss *= self.global_contrastive_weight

        flava_losses = FlavaLosses(
            mim=mim_loss,
            mlm=mlm_loss,
            itm=itm_loss,
            global_contrastive=gc_loss,
            mmm_image=mmm_image_loss,
            mmm_text=mmm_text_loss,
        )

        if return_loss and not flava_losses.all_none():
            total_loss = sum(loss if loss is not None else 0 for loss in flava_losses.values())

        if not return_dict:
            output = (
                image_embeddings,
                flava_output.image_output.to_tuple() if flava_output.image_output is not None else None,
                text_embeddings,
                flava_output.text_output.to_tuple() if flava_output.text_output is not None else None,
                flava_output.multimodal_embeddings,
                flava_output.multimodal_output.to_tuple() if flava_output.multimodal_output is not None else None,
                image_masked_embeddings,
                flava_masked_output.image_output.to_tuple() if flava_masked_output.image_output is not None else None,
                text_masked_embeddings,
                flava_masked_output.text_output.to_tuple() if flava_masked_output.text_output is not None else None,
                multimodal_masked_embeddings,
                flava_masked_output.multimodal_output.to_tuple()
                if flava_masked_output.multimodal_output is not None
                else None,
                mim_logits,
                mlm_logits,
                itm_logits,
                logits_per_image,
                logits_per_image,
                mmm_image_logits,
                mmm_text_logits,
            )
            if return_loss and not flava_losses.all_none():
                output = (
                    total_loss,
                    flava_losses,
                ) + output

            # Filter None as transformer by default won't handle it
            return tuple(x for x in output if x is None)

        return FlavaForPreTrainingOutput(
            loss=total_loss,
            loss_info=flava_losses,
            image_embeddings=image_embeddings,
            image_output=flava_output.image_output,
            text_embeddings=text_embeddings,
            text_output=flava_output.text_output,
            multimodal_embeddings=flava_output.multimodal_embeddings,
            multimodal_output=flava_output.multimodal_output,
            image_masked_embeddings=image_masked_embeddings,
            image_masked_output=flava_masked_output.image_output,
            text_masked_embeddings=text_masked_embeddings,
            text_masked_output=flava_masked_output.text_output,
            multimodal_masked_embeddings=multimodal_masked_embeddings,
            multimodal_masked_output=flava_masked_output.multimodal_output,
            mim_logits=mim_logits,
            mlm_logits=mlm_logits,
            itm_logits=itm_logits,
            contrastive_logits_per_image=logits_per_image,
            contrastive_logits_per_text=logits_per_text,
            mmm_image_logits=mmm_image_logits,
            mmm_text_logits=mmm_text_logits,
        )

__all__ = [
    "FlavaForPreTraining",
    "FlavaImageCodebook",
    "FlavaImageModel",
    "FlavaModel",
    "FlavaMultimodalModel",
    "FlavaPreTrainedModel",
    "FlavaTextModel",
]
