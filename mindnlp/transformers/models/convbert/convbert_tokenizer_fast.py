# Copyright 2023 Huawei Technologies Co., Ltd
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
# ============================================================================
"""Tokenization classes for ConvBERT."""
import json
from typing import List, Optional, Tuple

from tokenizers import normalizers

from ...tokenization_utils_fast import PreTrainedTokenizerFast
from .convbert_tokenizer import ConvBertTokenizer



VOCAB_FILES_NAMES = {"vocab_file": "vocab.txt"}

PRETRAINED_VOCAB_FILES_MAP = {
    "vocab_file": {
        "YituTech/conv-bert-base": "https://huggingface.co/YituTech/conv-bert-base/resolve/main/vocab.txt",
        "YituTech/conv-bert-medium-small": (
            "https://huggingface.co/YituTech/conv-bert-medium-small/resolve/main/vocab.txt"
        ),
        "YituTech/conv-bert-small": "https://huggingface.co/YituTech/conv-bert-small/resolve/main/vocab.txt",
    }
}

PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES = {
    "YituTech/conv-bert-base": 512,
    "YituTech/conv-bert-medium-small": 512,
    "YituTech/conv-bert-small": 512,
}


PRETRAINED_INIT_CONFIGURATION = {
    "YituTech/conv-bert-base": {"do_lower_case": True},
    "YituTech/conv-bert-medium-small": {"do_lower_case": True},
    "YituTech/conv-bert-small": {"do_lower_case": True},
}


# Copied from transformers.models.bert.tokenization_bert_fast.BertTokenizerFast with bert-base-cased->YituTech/conv-bert-base, Bert->ConvBert, BERT->ConvBERT
class ConvBertTokenizerFast(PreTrainedTokenizerFast):
    r"""
    Construct a "fast" ConvBERT tokenizer (backed by HuggingFace's *tokenizers* library). Based on WordPiece.

    This tokenizer inherits from [`PreTrainedTokenizerFast`] which contains most of the main methods. Users should
    refer to this superclass for more information regarding those methods.

    Args:
        vocab_file (`str`):
            File containing the vocabulary.
        do_lower_case (`bool`, *optional*, defaults to `True`):
            Whether or not to lowercase the input when tokenizing.
        unk_token (`str`, *optional*, defaults to `"[UNK]"`):
            The unknown token. A token that is not in the vocabulary cannot be converted to an ID and is set to be this
            token instead.
        sep_token (`str`, *optional*, defaults to `"[SEP]"`):
            The separator token, which is used when building a sequence from multiple sequences, e.g. two sequences for
            sequence classification or for a text and a question for question answering. It is also used as the last
            token of a sequence built with special tokens.
        pad_token (`str`, *optional*, defaults to `"[PAD]"`):
            The token used for padding, for example when batching sequences of different lengths.
        cls_token (`str`, *optional*, defaults to `"[CLS]"`):
            The classifier token which is used when doing sequence classification (classification of the whole sequence
            instead of per-token classification). It is the first token of the sequence when built with special tokens.
        mask_token (`str`, *optional*, defaults to `"[MASK]"`):
            The token used for masking values. This is the token used when training this model with masked language
            modeling. This is the token which the model will try to predict.
        clean_text (`bool`, *optional*, defaults to `True`):
            Whether or not to clean the text before tokenization by removing any control characters and replacing all
            whitespaces by the classic one.
        tokenize_chinese_chars (`bool`, *optional*, defaults to `True`):
            Whether or not to tokenize Chinese characters. This should likely be deactivated for Japanese (see [this
            issue](https://github.com/huggingface/transformers/issues/328)).
        strip_accents (`bool`, *optional*):
            Whether or not to strip all accents. If this option is not specified, then it will be determined by the
            value for `lowercase` (as in the original ConvBERT).
        wordpieces_prefix (`str`, *optional*, defaults to `"##"`):
            The prefix for subwords.
    """

    vocab_files_names = VOCAB_FILES_NAMES
    pretrained_vocab_files_map = PRETRAINED_VOCAB_FILES_MAP
    pretrained_init_configuration = PRETRAINED_INIT_CONFIGURATION
    max_model_input_sizes = PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES
    slow_tokenizer_class = ConvBertTokenizer

    def __init__(
        self,
        vocab_file=None,
        tokenizer_file=None,
        do_lower_case=True,
        unk_token="[UNK]",
        sep_token="[SEP]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        mask_token="[MASK]",
        tokenize_chinese_chars=True,
        strip_accents=None,
        **kwargs,
    ):

        """
        This method initializes an instance of the ConvBertTokenizerFast class.
        
        Args:
            self: The instance of the ConvBertTokenizerFast class.
            vocab_file (str): The path to the vocabulary file. Default is None.
            tokenizer_file (str): The path to the tokenizer file. Default is None.
            do_lower_case (bool): A flag indicating whether the text should be lowercased. Default is True.
            unk_token (str): The unknown token to be used. Default is '[UNK]'.
            sep_token (str): The separator token to be used. Default is '[SEP]'.
            pad_token (str): The padding token to be used. Default is '[PAD]'.
            cls_token (str): The classification token to be used. Default is '[CLS]'.
            mask_token (str): The mask token to be used. Default is '[MASK]'.
            tokenize_chinese_chars (bool): A flag indicating whether to tokenize Chinese characters. Default is True.
            strip_accents (str): A flag indicating whether to strip accents. Default is None.
            **kwargs: Additional keyword arguments.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            ValueError: If the normalizer state does not match the specified parameters.
            TypeError: If the normalizer class is not found or if an invalid argument type is provided.
            json.JSONDecodeError: If there is an error decoding the normalizer state from JSON format.
        """
        super().__init__(
            vocab_file,
            tokenizer_file=tokenizer_file,
            do_lower_case=do_lower_case,
            unk_token=unk_token,
            sep_token=sep_token,
            pad_token=pad_token,
            cls_token=cls_token,
            mask_token=mask_token,
            tokenize_chinese_chars=tokenize_chinese_chars,
            strip_accents=strip_accents,
            **kwargs,
        )

        normalizer_state = json.loads(self.backend_tokenizer.normalizer.__getstate__())
        if (
            normalizer_state.get("lowercase", do_lower_case) != do_lower_case
            or normalizer_state.get("strip_accents", strip_accents) != strip_accents
            or normalizer_state.get("handle_chinese_chars", tokenize_chinese_chars) != tokenize_chinese_chars
        ):
            normalizer_class = getattr(normalizers, normalizer_state.pop("type"))
            normalizer_state["lowercase"] = do_lower_case
            normalizer_state["strip_accents"] = strip_accents
            normalizer_state["handle_chinese_chars"] = tokenize_chinese_chars
            self.backend_tokenizer.normalizer = normalizer_class(**normalizer_state)

        self.do_lower_case = do_lower_case

    def build_inputs_with_special_tokens(self, token_ids_0, token_ids_1=None):
        """
        Build model inputs from a sequence or a pair of sequence for sequence classification tasks by concatenating and
        adding special tokens. A ConvBERT sequence has the following format:

        - single sequence: `[CLS] X [SEP]`
        - pair of sequences: `[CLS] A [SEP] B [SEP]`

        Args:
            token_ids_0 (`List[int]`):
                List of IDs to which the special tokens will be added.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: List of [input IDs](../glossary#input-ids) with the appropriate special tokens.
        """
        output = [self.cls_token_id] + token_ids_0 + [self.sep_token_id]

        if token_ids_1 is not None:
            output += token_ids_1 + [self.sep_token_id]

        return output

    def create_token_type_ids_from_sequences(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Create a mask from the two sequences passed to be used in a sequence-pair classification task. A ConvBERT sequence
        pair mask has the following format:

        ```
        0 0 0 0 0 0 0 0 0 0 0 1 1 1 1 1 1 1 1 1
        | first sequence    | second sequence |
        ```

        If `token_ids_1` is `None`, this method only returns the first portion of the mask (0s).

        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: List of [token type IDs](../glossary#token-type-ids) according to the given sequence(s).
        """
        sep = [self.sep_token_id]
        cls = [self.cls_token_id]
        if token_ids_1 is None:
            return len(cls + token_ids_0 + sep) * [0]
        return len(cls + token_ids_0 + sep) * [0] + len(token_ids_1 + sep) * [1]

    def save_vocabulary(self, save_directory: str, filename_prefix: Optional[str] = None) -> Tuple[str]:

        """
        Save the vocabulary files for the ConvBertTokenizerFast model.
        
        Args:
            self (ConvBertTokenizerFast): The instance of the ConvBertTokenizerFast class.
            save_directory (str): The directory where the vocabulary files will be saved.
            filename_prefix (Optional[str]): The prefix to be added to the vocabulary file names. Defaults to None.
        
        Returns:
            Tuple[str]: A tuple containing the file paths of the saved vocabulary files.
        
        Raises:
            (Exception): If an error occurs while saving the vocabulary files.
        """
        files = self._tokenizer.model.save(save_directory, name=filename_prefix)
        return tuple(files)

__all__ = ['ConvBertTokenizerFast']
