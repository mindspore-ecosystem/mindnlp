# coding=utf-8
# Copyright 2022 The HuggingFace Inc. team.
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
# ============================================================================
""" AutoImageProcessor class."""
import importlib
import json
import os
import warnings
from collections import OrderedDict
from typing import Dict, Optional, Union

# Build the list of all image processors
from mindnlp.utils import logging, get_file_from_repo
from mindnlp.configs import CONFIG_NAME, IMAGE_PROCESSOR_NAME
from ...configuration_utils import PretrainedConfig
from ...image_processing_utils import ImageProcessingMixin
from .auto_factory import _LazyAutoMapping
from .configuration_auto import (
    CONFIG_MAPPING_NAMES,
    AutoConfig,
    model_type_to_module_name,
    replace_list_option_in_docstrings,
)


logger = logging.get_logger(__name__)

IMAGE_PROCESSOR_MAPPING_NAMES = OrderedDict(
    [
        ("align", "EfficientNetImageProcessor"),
        ("beit", "BeitImageProcessor"),
        ("bit", "BitImageProcessor"),
        ("blip", "BlipImageProcessor"),
        ("blip-2", "BlipImageProcessor"),
        ("bridgetower", "BridgeTowerImageProcessor"),
        # ("chinese_clip", "ChineseCLIPImageProcessor"),
        ("clip", "CLIPImageProcessor"),
        # ("clipseg", "ViTImageProcessor"),
        # ("conditional_detr", "ConditionalDetrImageProcessor"),
        ("convnext", "ConvNextImageProcessor"),
        # ("convnextv2", "ConvNextImageProcessor"),
        ("cvt", "ConvNextImageProcessor"),
        # ("data2vec-vision", "BeitImageProcessor"),
        # ("deformable_detr", "DeformableDetrImageProcessor"),
        ("deit", "DeiTImageProcessor"),
        # ("depth_anything", "DPTImageProcessor"),
        # ("deta", "DetaImageProcessor"),
        ("detr", "DetrImageProcessor"),
        # ("dinat", "ViTImageProcessor"),
        # ("dinov2", "BitImageProcessor"),
        # ("donut-swin", "DonutImageProcessor"),
        # ("dpt", "DPTImageProcessor"),
        ("efficientformer", "EfficientFormerImageProcessor"),
        ("efficientnet", "EfficientNetImageProcessor"),
        ("flava", "FlavaImageProcessor"),
        ("focalnet", "BitImageProcessor"),
        # ("fuyu", "FuyuImageProcessor"),
        ("git", "CLIPImageProcessor"),
        # ("glpn", "GLPNImageProcessor"),
        ("groupvit", "CLIPImageProcessor"),
        # ("idefics", "IdeficsImageProcessor"),
        ("imagegpt", "ImageGPTImageProcessor"),
        # ("instructblip", "BlipImageProcessor"),
        ("kosmos-2", "CLIPImageProcessor"),
        ("layoutlmv2", "LayoutLMv2ImageProcessor"),
        ("layoutlmv3", "LayoutLMv3ImageProcessor"),
        # ("levit", "LevitImageProcessor"),
        ("llava", "CLIPImageProcessor"),
        ("mask2former", "Mask2FormerImageProcessor"),
        ("maskformer", "MaskFormerImageProcessor"),
        # ("mgp-str", "ViTImageProcessor"),
        # ("mobilenet_v1", "MobileNetV1ImageProcessor"),
        # ("mobilenet_v2", "MobileNetV2ImageProcessor"),
        ("mobilevit", "MobileViTImageProcessor"),
        # ("mobilevitv2", "MobileViTImageProcessor"),
        # ("nat", "ViTImageProcessor"),
        ("nougat", "NougatImageProcessor"),
        ("oneformer", "OneFormerImageProcessor"),
        # ("owlv2", "Owlv2ImageProcessor"),
        ("owlvit", "OwlViTImageProcessor"),
        # ("perceiver", "PerceiverImageProcessor"),
        # ("pix2struct", "Pix2StructImageProcessor"),
        ("poolformer", "PoolFormerImageProcessor"),
        # ("pvt", "PvtImageProcessor"),
        # ("pvt_v2", "PvtImageProcessor"),
        ("regnet", "ConvNextImageProcessor"),
        ("resnet", "ConvNextImageProcessor"),
        ("sam", "SamImageProcessor"),
        ("segformer", "SegformerImageProcessor"),
        # ("seggpt", "SegGptImageProcessor"),
        # ("siglip", "SiglipImageProcessor"),
        ("swiftformer", "ViTImageProcessor"),
        ("swin", "ViTImageProcessor"),
        # ("swin2sr", "Swin2SRImageProcessor"),
        # ("swinv2", "ViTImageProcessor"),
        ("table-transformer", "DetrImageProcessor"),
        ("timesformer", "VideoMAEImageProcessor"),
        # ("tvlt", "TvltImageProcessor"),
        # ("tvp", "TvpImageProcessor"),
        ("udop", "LayoutLMv3ImageProcessor"),
        # ("upernet", "SegformerImageProcessor"),
        ("van", "ConvNextImageProcessor"),
        ("videomae", "VideoMAEImageProcessor"),
        # ("vilt", "ViltImageProcessor"),
        ("vipllava", "CLIPImageProcessor"),
        ("vit", "ViTImageProcessor"),
        ("vit_hybrid", "ViTHybridImageProcessor"),
        # ("vit_mae", "ViTImageProcessor"),
        # ("vit_msn", "ViTImageProcessor"),
        # ("vitmatte", "VitMatteImageProcessor"),
        ("xclip", "CLIPImageProcessor"),
        # ("yolos", "YolosImageProcessor"),
    ]
)

IMAGE_PROCESSOR_MAPPING = _LazyAutoMapping(CONFIG_MAPPING_NAMES, IMAGE_PROCESSOR_MAPPING_NAMES)


def image_processor_class_from_name(class_name: str):
    """
    Args:
        class_name (str): The name of the image processor class to retrieve.
            It is used to locate and import the corresponding class based on the provided name.

    Returns:
        None: If the class with the given name is not found, None is returned.

    Raises:
        AttributeError: If an attribute error occurs while attempting to retrieve the class from the imported module.
        ImportError: If an import error occurs while attempting to import the module.
    """
    for module_name, extractors in IMAGE_PROCESSOR_MAPPING_NAMES.items():
        if class_name in extractors:
            module_name = model_type_to_module_name(module_name)

            module = importlib.import_module(f".{module_name}", "mindnlp.transformers.models")
            try:
                return getattr(module, class_name)
            except AttributeError:
                continue

    for _, extractor in IMAGE_PROCESSOR_MAPPING._extra_content.items():
        if getattr(extractor, "__name__", None) == class_name:
            return extractor

    # We did not fine the class, but maybe it's because a dep is missing. In that case, the class will be in the main
    # init and we return the proper dummy to get an appropriate error message.
    main_module = importlib.import_module("mindnlp.transformers")
    if hasattr(main_module, class_name):
        return getattr(main_module, class_name)

    return None


def get_image_processor_config(
    pretrained_model_name_or_path: Union[str, os.PathLike],
    cache_dir: Optional[Union[str, os.PathLike]] = None,
    force_download: bool = False,
    resume_download: bool = False,
    proxies: Optional[Dict[str, str]] = None,
    token: Optional[Union[bool, str]] = None,
    revision: Optional[str] = None,
    local_files_only: bool = False,
    **kwargs,
):
    """
    Loads the image processor configuration from a pretrained model image processor configuration.

    Args:
        pretrained_model_name_or_path (`str` or `os.PathLike`):
            This can be either:

            - a string, the *model id* of a pretrained model configuration hosted inside a model repo on
              hf-mirror.com.
            - a path to a *directory* containing a configuration file saved using the
              [`~PreTrainedTokenizer.save_pretrained`] method, e.g., `./my_model_directory/`.

        cache_dir (`str` or `os.PathLike`, *optional*):
            Path to a directory in which a downloaded pretrained model configuration should be cached if the standard
            cache should not be used.
        force_download (`bool`, *optional*, defaults to `False`):
            Whether or not to force to (re-)download the configuration files and override the cached versions if they
            exist.
        resume_download (`bool`, *optional*, defaults to `False`):
            Whether or not to delete incompletely received file. Attempts to resume the download if such a file exists.
        proxies (`Dict[str, str]`, *optional*):
            A dictionary of proxy servers to use by protocol or endpoint, e.g., `{'http': 'foo.bar:3128',
            'http://hostname': 'foo.bar:4012'}.` The proxies are used on each request.
        token (`str` or *bool*, *optional*):
            The token to use as HTTP bearer authorization for remote files. If `True`, will use the token generated
            when running `huggingface-cli login` (stored in `~/.huggingface`).
        revision (`str`, *optional*, defaults to `"main"`):
            The specific model version to use. It can be a branch name, a tag name, or a commit id, since we use a
            git-based system for storing models and other artifacts on hf-mirror.com, so `revision` can be any
            identifier allowed by git.
        local_files_only (`bool`, *optional*, defaults to `False`):
            If `True`, will only try to load the image processor configuration from local files.

    <Tip>

    Passing `token=True` is required when you want to use a private model.

    </Tip>

    Returns:
        `Dict`: The configuration of the image processor.

    Example:
        ```python
        >>> # Download configuration from hf-mirror.com and cache.
        >>> image_processor_config = get_image_processor_config("google-bert/bert-base-uncased")
        >>> # This model does not have a image processor config so the result will be an empty dict.
        >>> image_processor_config = get_image_processor_config("FacebookAI/xlm-roberta-base")
        ...
        >>> # Save a pretrained image processor locally and you can reload its config
        >>> from transformers import AutoTokenizer
        ...
        >>> image_processor = AutoImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")
        >>> image_processor.save_pretrained("image-processor-test")
        >>> image_processor_config = get_image_processor_config("image-processor-test")
        ```
    """
    use_auth_token = kwargs.pop("use_auth_token", None)
    if use_auth_token is not None:
        warnings.warn(
            "The `use_auth_token` argument is deprecated and will be removed in v5 of Transformers. Please use `token` instead.",
            FutureWarning,
        )
        if token is not None:
            raise ValueError("`token` and `use_auth_token` are both specified. Please set only the argument `token`.")
        token = use_auth_token

    resolved_config_file = get_file_from_repo(
        pretrained_model_name_or_path,
        IMAGE_PROCESSOR_NAME,
        cache_dir=cache_dir,
        force_download=force_download,
        resume_download=resume_download,
        proxies=proxies,
        token=token,
        revision=revision,
        local_files_only=local_files_only,
    )
    if resolved_config_file is None:
        logger.info(
            "Could not locate the image processor configuration file, will try to use the model config instead."
        )
        return {}

    with open(resolved_config_file, encoding="utf-8") as reader:
        return json.load(reader)


class AutoImageProcessor:
    r"""
    This is a generic image processor class that will be instantiated as one of the image processor classes of the
    library when created with the [`AutoImageProcessor.from_pretrained`] class method.

    This class cannot be instantiated directly using `__init__()` (throws an error).
    """
    def __init__(self):
        """
        Initializes an instance of AutoImageProcessor.

        Args:
            self: The object itself.

        Returns:
            None.
        Raises:
            EnvironmentError:
                Raised when attempting to directly instantiate an AutoImageProcessor object.
                AutoImageProcessor is designed to be instantiated using the
                `AutoImageProcessor.from_pretrained(pretrained_model_name_or_path)` method.
        """
        raise EnvironmentError(
            "AutoImageProcessor is designed to be instantiated "
            "using the `AutoImageProcessor.from_pretrained(pretrained_model_name_or_path)` method."
        )

    @classmethod
    @replace_list_option_in_docstrings(IMAGE_PROCESSOR_MAPPING_NAMES)
    def from_pretrained(cls, pretrained_model_name_or_path, **kwargs):
        r"""
        Instantiate one of the image processor classes of the library from a pretrained model vocabulary.

        The image processor class to instantiate is selected based on the `model_type` property of the config object
        (either passed as an argument or loaded from `pretrained_model_name_or_path` if possible), or when it's
        missing, by falling back to using pattern matching on `pretrained_model_name_or_path`:

        List options

        Params:
            pretrained_model_name_or_path (`str` or `os.PathLike`):
                This can be either:

                - a string, the *model id* of a pretrained image_processor hosted inside a model repo on
                  hf-mirror.com.
                - a path to a *directory* containing a image processor file saved using the
                  [`~image_processing_utils.ImageProcessingMixin.save_pretrained`] method, e.g.,
                  `./my_model_directory/`.
                - a path or url to a saved image processor JSON *file*, e.g.,
                  `./my_model_directory/preprocessor_config.json`.
            cache_dir (`str` or `os.PathLike`, *optional*):
                Path to a directory in which a downloaded pretrained model image processor should be cached if the
                standard cache should not be used.
            force_download (`bool`, *optional*, defaults to `False`):
                Whether or not to force to (re-)download the image processor files and override the cached versions if
                they exist.
            resume_download (`bool`, *optional*, defaults to `False`):
                Whether or not to delete incompletely received file. Attempts to resume the download if such a file
                exists.
            proxies (`Dict[str, str]`, *optional*):
                A dictionary of proxy servers to use by protocol or endpoint, e.g., `{'http': 'foo.bar:3128',
                'http://hostname': 'foo.bar:4012'}.` The proxies are used on each request.
            token (`str` or *bool*, *optional*):
                The token to use as HTTP bearer authorization for remote files. If `True`, will use the token generated
                when running `huggingface-cli login` (stored in `~/.huggingface`).
            revision (`str`, *optional*, defaults to `"main"`):
                The specific model version to use. It can be a branch name, a tag name, or a commit id, since we use a
                git-based system for storing models and other artifacts on hf-mirror.com, so `revision` can be any
                identifier allowed by git.
            return_unused_kwargs (`bool`, *optional*, defaults to `False`):
                If `False`, then this function returns just the final image processor object. If `True`, then this
                functions returns a `Tuple(image_processor, unused_kwargs)` where *unused_kwargs* is a dictionary
                consisting of the key/value pairs whose keys are not image processor attributes: i.e., the part of
                `kwargs` which has not been used to update `image_processor` and is otherwise ignored.
            trust_remote_code (`bool`, *optional*, defaults to `False`):
                Whether or not to allow for custom models defined on the Hub in their own modeling files. This option
                should only be set to `True` for repositories you trust and in which you have read the code, as it will
                execute code present on the Hub on your local machine.
            kwargs (`Dict[str, Any]`, *optional*):
                The values in kwargs of any keys which are image processor attributes will be used to override the
                loaded values. Behavior concerning key/value pairs whose keys are *not* image processor attributes is
                controlled by the `return_unused_kwargs` keyword parameter.

        <Tip>

        Passing `token=True` is required when you want to use a private model.

        </Tip>

        Example:
            ```python
            >>> from transformers import AutoImageProcessor
            ...
            >>> # Download image processor from hf-mirror.com and cache.
            >>> image_processor = AutoImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")
            ...
            >>> # If image processor files are in a directory (e.g. image processor was saved using *save_pretrained('./test/saved_model/')*)
            >>> # image_processor = AutoImageProcessor.from_pretrained("./test/saved_model/")
            ```
        """
        use_auth_token = kwargs.pop("use_auth_token", None)
        if use_auth_token is not None:
            warnings.warn(
                "The `use_auth_token` argument is deprecated and will be removed in v5 of Transformers. Please use `token` instead.",
                FutureWarning,
            )
            if kwargs.get("token", None) is not None:
                raise ValueError(
                    "`token` and `use_auth_token` are both specified. Please set only the argument `token`."
                )
            kwargs["token"] = use_auth_token

        config = kwargs.pop("config", None)
        kwargs["_from_auto"] = True

        config_dict, _ = ImageProcessingMixin.get_image_processor_dict(pretrained_model_name_or_path, **kwargs)
        image_processor_class = config_dict.get("image_processor_type", None)
        image_processor_auto_map = None
        if "AutoImageProcessor" in config_dict.get("auto_map", {}):
            image_processor_auto_map = config_dict["auto_map"]["AutoImageProcessor"]

        # If we still don't have the image processor class, check if we're loading from a previous feature extractor config
        # and if so, infer the image processor class from there.
        if image_processor_class is None and image_processor_auto_map is None:
            feature_extractor_class = config_dict.pop("feature_extractor_type", None)
            if feature_extractor_class is not None:
                logger.warning(
                    "Could not find image processor class in the image processor config or the model config. Loading "
                    "based on pattern matching with the model's feature extractor configuration. Please open a "
                    "PR/issue to update `preprocessor_config.json` to use `image_processor_type` instead of "
                    "`feature_extractor_type`. This warning will be removed in v4.40."
                )
                image_processor_class = feature_extractor_class.replace("FeatureExtractor", "ImageProcessor")
            if "AutoFeatureExtractor" in config_dict.get("auto_map", {}):
                feature_extractor_auto_map = config_dict["auto_map"]["AutoFeatureExtractor"]
                image_processor_auto_map = feature_extractor_auto_map.replace("FeatureExtractor", "ImageProcessor")
                logger.warning(
                    "Could not find image processor auto map in the image processor config or the model config. "
                    "Loading based on pattern matching with the model's feature extractor configuration. Please open a "
                    "PR/issue to update `preprocessor_config.json` to use `AutoImageProcessor` instead of "
                    "`AutoFeatureExtractor`. This warning will be removed in v4.40."
                )

        print(image_processor_class)
        # If we don't find the image processor class in the image processor config, let's try the model config.
        if image_processor_class is None and image_processor_auto_map is None:
            if not isinstance(config, PretrainedConfig):
                config = AutoConfig.from_pretrained(pretrained_model_name_or_path, **kwargs)
            # It could be in `config.image_processor_type``
            image_processor_class = getattr(config, "image_processor_type", None)
            if hasattr(config, "auto_map") and "AutoImageProcessor" in config.auto_map:
                image_processor_auto_map = config.auto_map["AutoImageProcessor"]

        if image_processor_class is not None:
            image_processor_class = image_processor_class_from_name(image_processor_class)

        if image_processor_class is not None:
            return image_processor_class.from_dict(config_dict, **kwargs)
        # Last try: we use the IMAGE_PROCESSOR_MAPPING.
        if type(config) in IMAGE_PROCESSOR_MAPPING:
            image_processor_class = IMAGE_PROCESSOR_MAPPING[type(config)]
            return image_processor_class.from_dict(config_dict, **kwargs)

        raise ValueError(
            f"Unrecognized image processor in {pretrained_model_name_or_path}. Should have a "
            f"`image_processor_type` key in its {IMAGE_PROCESSOR_NAME} of {CONFIG_NAME}, or one of the following "
            f"`model_type` keys in its {CONFIG_NAME}: {', '.join(c for c in IMAGE_PROCESSOR_MAPPING_NAMES.keys())}"
        )

    @staticmethod
    def register(config_class, image_processor_class, exist_ok=False):
        """
        Register a new image processor for this class.

        Args:
            config_class ([`PretrainedConfig`]):
                The configuration corresponding to the model to register.
            image_processor_class ([`ImageProcessingMixin`]): The image processor to register.
        """
        IMAGE_PROCESSOR_MAPPING.register(config_class, image_processor_class, exist_ok=exist_ok)
