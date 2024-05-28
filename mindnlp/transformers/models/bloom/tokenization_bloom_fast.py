# coding=utf-8
# Copyright 2022 The HuggingFace Inc. team.
# Copyright 2024 Huawei Technologies Co., Ltd
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
"""Tokenization classes for Bloom."""


import pickle
from typing import Optional, Tuple

from mindnlp.utils import logging
from ...tokenization_utils_base import BatchEncoding
from ...tokenization_utils_fast import PreTrainedTokenizerFast


logger = logging.get_logger(__name__)

VOCAB_FILES_NAMES = {"tokenizer_file": "tokenizer.json"}

PRETRAINED_VOCAB_FILES_MAP = {
    "tokenizer_file": {
        "bigscience/tokenizer": "https://hf-mirror.com/bigscience/tokenizer/blob/main/tokenizer.json",
        "bigscience/bloom-560m": "https://hf-mirror.com/bigscience/bloom-560m/blob/main/tokenizer.json",
        "bigscience/bloom-1b1": "https://hf-mirror.com/bigscience/bloom-1b1/blob/main/tokenizer.json",
        "bigscience/bloom-1b7": "https://hf-mirror.com/bigscience/bloom-1b7/blob/main/tokenizer.json",
        "bigscience/bloom-3b": "https://hf-mirror.com/bigscience/bloom-3b/blob/main/tokenizer.json",
        "bigscience/bloom-7b1": "https://hf-mirror.com/bigscience/bloom-7b1/blob/main/tokenizer.json",
        "bigscience/bloom": "https://hf-mirror.com/bigscience/bloom/blob/main/tokenizer.json",
    },
}


class BloomTokenizerFast(PreTrainedTokenizerFast):
    """
    Construct a "fast" Bloom tokenizer (backed by HuggingFace's *tokenizers* library). Based on byte-level
    Byte-Pair-Encoding.

    This tokenizer has been trained to treat spaces like parts of the tokens (a bit like sentencepiece) so a word will
    be encoded differently whether it is at the beginning of the sentence (without space) or not:

    ```python
    >>> from transformers import BloomTokenizerFast

    >>> tokenizer = BloomTokenizerFast.from_pretrained("bigscience/bloom")
    >>> tokenizer("Hello world")["input_ids"]
    [59414, 8876]

    >>> tokenizer(" Hello world")["input_ids"]
    [86153, 8876]
    ```

    You can get around that behavior by passing `add_prefix_space=True` when instantiating this tokenizer, but since
    the model was not pretrained this way, it might yield a decrease in performance.

    <Tip>

    When used with `is_split_into_words=True`, this tokenizer needs to be instantiated with `add_prefix_space=True`.

    </Tip>

    This tokenizer inherits from [`PreTrainedTokenizerFast`] which contains most of the main methods. Users should
    refer to this superclass for more information regarding those methods.

    Args:
        vocab_file (`str`):
            Path to the vocabulary file.
        merges_file (`str`):
            Path to the merges file.
        errors (`str`, *optional*, defaults to `"replace"`):
            Paradigm to follow when decoding bytes to UTF-8. See
            [bytes.decode](https://docs.python.org/3/library/stdtypes.html#bytes.decode) for more information.
        unk_token (`str`, *optional*, defaults to `<|endoftext|>`):
            The unknown token. A token that is not in the vocabulary cannot be converted to an ID and is set to be this
            token instead.
        bos_token (`str`, *optional*, defaults to `<|endoftext|>`):
            The beginning of sequence token.
        eos_token (`str`, *optional*, defaults to `<|endoftext|>`):
            The end of sequence token.
        add_prefix_space (`bool`, *optional*, defaults to `False`):
            Whether or not to add an initial space to the input. This allows to treat the leading word just as any
            other word. (Bloom tokenizer detect beginning of words by the preceding space).
        trim_offsets (`bool`, *optional*, defaults to `True`):
            Whether or not the post-processing step should trim offsets to avoid including whitespaces.
    """
    vocab_files_names = VOCAB_FILES_NAMES
    pretrained_vocab_files_map = PRETRAINED_VOCAB_FILES_MAP
    model_input_names = ["input_ids", "attention_mask"]
    slow_tokenizer_class = None
    # No `max_model_input_sizes` as BLOOM uses ALiBi positional embeddings

    def __init__(
        self,
        vocab_file=None,
        merges_file=None,
        tokenizer_file=None,
        unk_token="<unk>",
        bos_token="<s>",
        eos_token="</s>",
        pad_token="<pad>",
        add_prefix_space=False,
        clean_up_tokenization_spaces=False,
        **kwargs,
    ):
        """
        Initialize a BloomTokenizerFast object.
        
        Args:
        - self: The instance of the class.
        - vocab_file (str): Path to a vocabulary file.
        - merges_file (str): Path to a merges file.
        - tokenizer_file (str): Path to a tokenizer file.
        - unk_token (str): The unknown token.
        - bos_token (str): The beginning of sequence token.
        - eos_token (str): The end of sequence token.
        - pad_token (str): The padding token.
        - add_prefix_space (bool): Flag indicating whether to add prefix space.
        - clean_up_tokenization_spaces (bool): Flag indicating whether to clean up tokenization spaces.
        
        Returns:
        - None: This method does not return any value.
        
        Raises:
        - None: This method does not explicitly raise any exceptions.
        """
        super().__init__(
            vocab_file,
            merges_file,
            tokenizer_file=tokenizer_file,
            unk_token=unk_token,
            bos_token=bos_token,
            eos_token=eos_token,
            pad_token=pad_token,
            add_prefix_space=add_prefix_space,
            clean_up_tokenization_spaces=clean_up_tokenization_spaces,
            **kwargs,
        )
        # TODO @ArthurZucker this can only work one way for now, to update later-on. Tests should also properly
        # check this as they were green before.
        pre_tok_state = pickle.dumps(self.backend_tokenizer.pre_tokenizer)
        decoder_state = pickle.dumps(self.backend_tokenizer.decoder)

        if add_prefix_space:
            pre_tok_state = pre_tok_state.replace(b'"add_prefix_space":false', b'"add_prefix_space": true')
            decoder_state = decoder_state.replace(b'"add_prefix_space":false', b'"add_prefix_space": true')
        self.backend_tokenizer.pre_tokenizer = pickle.loads(pre_tok_state)
        self.backend_tokenizer.decoder = pickle.loads(decoder_state)

        self.add_prefix_space = add_prefix_space

    def _batch_encode_plus(self, *args, **kwargs) -> BatchEncoding:
        """
        The `_batch_encode_plus` method is used in the `BloomTokenizerFast` class to encode a batch of inputs into a `BatchEncoding` object.
        
        Args:
            self: The instance of the `BloomTokenizerFast` class.
            
        Returns:
            A `BatchEncoding` object that contains the encoded representations of the inputs.
            
        Raises:
            Exception: If the `add_prefix_space` parameter is False and `is_split_into_words` is True. In this case, the `BloomTokenizerFast` class needs to be instantiated with `add_prefix_space=True` to work
with pretokenized inputs.
        """
        is_split_into_words = kwargs.get("is_split_into_words", False)
        if not (self.add_prefix_space or not is_split_into_words):
            raise Exception(
                f"You need to instantiate {self.__class__.__name__} with add_prefix_space=True to use it with"
                " pretokenized inputs."
            )

        return super()._batch_encode_plus(*args, **kwargs)

    def _encode_plus(self, *args, **kwargs) -> BatchEncoding:
        """
        Encodes the input sequence into a batch of encoded sequences using the BloomTokenizerFast.
        
        Args:
            self (BloomTokenizerFast): An instance of the BloomTokenizerFast class.
        
        Returns:
            BatchEncoding: A batch of encoded sequences.
        
        Raises:
            Exception: If the BloomTokenizerFast instance is not instantiated with add_prefix_space=True and the input is pretokenized.
        
        Note:
            This method is used to encode the input sequence into a batch of encoded sequences. It checks if the BloomTokenizerFast instance is instantiated with add_prefix_space=True and the input is not
pretokenized. If not, it raises an exception.
        
        Example:
            
            tokenizer = BloomTokenizerFast(add_prefix_space=True)
            encoding = tokenizer._encode_plus(input_sequence)
            
        """
        is_split_into_words = kwargs.get("is_split_into_words", False)

        if not (self.add_prefix_space or not is_split_into_words):
            raise Exception(
                f"You need to instantiate {self.__class__.__name__} with add_prefix_space=True to use it with"
                " pretokenized inputs."
            )

        return super()._encode_plus(*args, **kwargs)

    def save_vocabulary(self, save_directory: str, filename_prefix: Optional[str] = None) -> Tuple[str]:
        """
        Save the tokenizer's vocabulary to a specified directory.
        
        Args:
            self (BloomTokenizerFast): An instance of the BloomTokenizerFast class.
            save_directory (str): The directory where the vocabulary files will be saved.
            filename_prefix (Optional[str], optional): A prefix to prepend to the vocabulary file names. Defaults to None.
        
        Returns:
            Tuple[str]: A tuple of file names that were saved in the specified directory.
        
        Raises:
            None
        
        The 'save_vocabulary' method saves the tokenizer's vocabulary to the specified 'save_directory'. 
        The vocabulary files are saved using the 'filename_prefix' if provided, or a default name if not specified.
        
        Example:
            tokenizer = BloomTokenizerFast()
            tokenizer.save_vocabulary('/path/to/save', 'vocab_')
            
            This will save the tokenizer's vocabulary files in the '/path/to/save' directory with file names
            prefixed by 'vocab_'. The method returns a tuple of file names that were saved.
        """
        files = self._tokenizer.model.save(save_directory, name=filename_prefix)
        return tuple(files)

    @property
    # Copied from transformers.models.gpt2.tokenization_gpt2.GPT2Tokenizer.default_chat_template
    def default_chat_template(self):
        """
        A simple chat template that ignores role information and just concatenates messages with EOS tokens.
        """
        logger.warning_once(
            "\nNo chat template is defined for this tokenizer - using the default template "
            f"for the {self.__class__.__name__} class. If the default is not appropriate for "
            "your model, please set `tokenizer.chat_template` to an appropriate template. "
            "See https://hf-mirror.com/docs/transformers/main/chat_templating for more information.\n"
        )
        return "{% for message in messages %}" "{{ message.content }}{{ eos_token }}" "{% endfor %}"

__all__ = ['BloomTokenizerFast']
