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
""" Llava-NeXT model configuration"""

from ...configuration_utils import PretrainedConfig
from ....utils import logging
from ..auto import CONFIG_MAPPING


logger = logging.get_logger(__name__)


class LlavaNextConfig(PretrainedConfig):
    r"""
    This is the configuration class to store the configuration of a [`LlavaNextForConditionalGeneration`]. It is used to instantiate an
    Llava-NeXT model according to the specified arguments, defining the model architecture. Instantiating a configuration
    with the defaults will yield a similar configuration to that of the [llava-hf/llava-v1.6-mistral-7b-hf](https://huggingface.co/llava-hf/llava-v1.6-mistral-7b-hf)
    model.

    Configuration objects inherit from [`PretrainedConfig`] and can be used to control the model outputs. Read the
    documentation from [`PretrainedConfig`] for more information.

    Args:
        vision_config (`Union[AutoConfig, dict]`,  *optional*, defaults to `CLIPVisionConfig`):
            The config object or dictionary of the vision backbone.
        text_config (`Union[AutoConfig, dict]`, *optional*, defaults to `LlamaConfig`):
            The config object or dictionary of the text backbone.
        ignore_index (`int`, *optional*, defaults to -100):
            The ignore index for the loss function.
        image_token_index (`int`, *optional*, defaults to 32000):
            The image token index to encode the image prompt.
        projector_hidden_act (`str`, *optional*, defaults to `"gelu"`):
            The activation function used by the multimodal projector.
        vision_feature_select_strategy (`str`, *optional*, defaults to `"default"`):
            The feature selection strategy used to select the vision feature from the vision backbone.
            Can be one of `"default"` or `"full"`. If `"default"`, the CLS token is removed from the vision features.
            If `"full"`, the full vision features are used.
        vision_feature_layer (`int`, *optional*, defaults to -2):
            The index of the layer to select the vision feature.
        image_grid_pinpoints (`List`, *optional*, defaults to `[[336, 672], [672, 336], [672, 672], [1008, 336], [336, 1008]]`):
            A list of possible resolutions to use for processing high resolution images. Each item in the list should be a tuple or list
            of the form `(height, width)`.

    Example:
        ```python
        >>> from transformers import LlavaNextForConditionalGeneration, LlavaNextConfig, CLIPVisionConfig, LlamaConfig

        >>> # Initializing a CLIP-vision config
        >>> vision_config = CLIPVisionConfig()

        >>> # Initializing a Llama config
        >>> text_config = LlamaConfig()

        >>> # Initializing a Llava-Next llava-hf/llava-v1.6-mistral-7b-hf style configuration
        >>> configuration = LlavaNextConfig(vision_config, text_config)

        >>> # Initializing a model from the llava-hf/llava-v1.6-mistral-7b-hf style configuration
        >>> model = LlavaNextForConditionalGeneration(configuration)

        >>> # Accessing the model configuration
        >>> configuration = model.config
        ```
    """
    model_type = "llava_next"
    is_composition = False

    def __init__(
        self,
        vision_config=None,
        text_config=None,
        ignore_index=-100,
        image_token_index=32000,
        projector_hidden_act="gelu",
        vision_feature_select_strategy="default",
        vision_feature_layer=-2,
        image_grid_pinpoints=None,
        **kwargs,
    ):
        """
        This method initializes an instance of the LlavaNextConfig class with the provided parameters.
        
        Args:
            self: The instance of the class.
            vision_config (dict, optional): Configuration settings for the vision model. If not provided, default settings will be used.
            text_config (dict, optional): Configuration settings for the text model. If not provided, default settings will be used.
            ignore_index (int, optional): Index to ignore during computation. Default is -100.
            image_token_index (int, optional): Index for image token. Default is 32000.
            projector_hidden_act (str, optional): Activation function for hidden layers in projector. Default is 'gelu'.
            vision_feature_select_strategy (str): Strategy for selecting vision features. Should be one of 'default' or 'full'.
            vision_feature_layer (int, optional): Layer to extract features from in the vision model.
            image_grid_pinpoints (list of lists, optional): Coordinates for image grid pinpoints. Default is [[336, 672], [672, 336], [672, 672], [1008, 336], [336, 1008].
        
        Returns:
            None
        
        Raises:
            - ValueError: If vision_feature_select_strategy is not 'default' or 'full'.
        """
        self.ignore_index = ignore_index
        self.image_token_index = image_token_index
        self.projector_hidden_act = projector_hidden_act

        if vision_feature_select_strategy not in ["default", "full"]:
            raise ValueError(
                "vision_feature_select_strategy should be one of 'default', 'full'."
                f"Got: {vision_feature_select_strategy}"
            )

        self.vision_feature_select_strategy = vision_feature_select_strategy
        self.vision_feature_layer = vision_feature_layer
        image_grid_pinpoints = (
            image_grid_pinpoints
            if image_grid_pinpoints is not None
            else [[336, 672], [672, 336], [672, 672], [1008, 336], [336, 1008]]
        )
        self.image_grid_pinpoints = image_grid_pinpoints

        if isinstance(vision_config, dict):
            vision_config["model_type"] = (
                vision_config["model_type"] if "model_type" in vision_config else "clip_vision_model"
            )
            vision_config = CONFIG_MAPPING[vision_config["model_type"]](
                **vision_config)
        elif vision_config is None:
            vision_config = CONFIG_MAPPING["clip_vision_model"](
                intermediate_size=4096,
                hidden_size=1024,
                patch_size=14,
                image_size=336,
                num_hidden_layers=24,
                num_attention_heads=16,
                vocab_size=32000,
                projection_dim=768,
            )

        self.vision_config = vision_config

        if isinstance(text_config, dict):
            text_config["model_type"] = text_config["model_type"] if "model_type" in text_config else "llama"
            text_config = CONFIG_MAPPING[text_config["model_type"]](
                **text_config)
        elif text_config is None:
            text_config = CONFIG_MAPPING["llama"]()

        self.text_config = text_config

        super().__init__(**kwargs)


__all__ = [
    "LlavaNextConfig",
]
