# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team. All rights reserved.
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
"""Fast Tokenization class for SeamlessM4T."""
import os
from shutil import copyfile
from typing import List, Optional, Tuple, Union

from tokenizers import processors

from mindnlp.utils import PaddingStrategy, is_sentencepiece_available, logging
from ...tokenization_utils import (
    BatchEncoding,
    PreTokenizedInput,
    TextInput,
)
from ...tokenization_utils_fast import PreTrainedTokenizerFast


if is_sentencepiece_available():
    from .tokenization_seamless_m4t import SeamlessM4TTokenizer
else:
    SeamlessM4TTokenizer = None

logger = logging.get_logger(__name__)

VOCAB_FILES_NAMES = {"vocab_file": "sentencepiece.bpe.model", "tokenizer_file": "tokenizer.json"}

PRETRAINED_VOCAB_FILES_MAP = {
    "vocab_file": {
        "facebook/hf-seamless-m4t-medium": "https://hf-mirror.com/facebook/hf-seamless-m4t-medium/resolve/main/vocab.txt",
    },
    "tokenizer_file": {
        "facebook/hf-seamless-m4t-medium": "https://hf-mirror.com/facebook/hf-seamless-m4t-medium/resolve/main/tokenizer.json",
    },
}

PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES = {
    "facebook/hf-seamless-m4t-medium": 2048,
}


class SeamlessM4TTokenizerFast(PreTrainedTokenizerFast):
    """
    Construct a "fast" SeamlessM4T tokenizer (backed by HuggingFace's *tokenizers* library). Based on
    [BPE](https://hf-mirror.com/docs/tokenizers/python/latest/components.html?highlight=BPE#models).

    This tokenizer inherits from [`PreTrainedTokenizerFast`] which contains most of the main methods. Users should
    refer to this superclass for more information regarding those methods.

    The tokenization method is `<language code> <tokens> <eos>` for source language documents, and `<eos> <language
    code> <tokens> <eos>` for target language documents.

    Example:
        ```python
        >>> from transformers import SeamlessM4TTokenizerFast

        >>> tokenizer = SeamlessM4TTokenizerFast.from_pretrained(
        ...     "facebook/hf-seamless-m4t-medium", src_lang="eng", tgt_lang="fra"
        ... )
        >>> example_english_phrase = " UN Chief Says There Is No Military Solution in Syria"
        >>> expected_translation_french = "Le chef de l'ONU affirme qu'il n'y a pas de solution militaire en Syrie."
        >>> inputs = tokenizer(example_english_phrase, text_target=expected_translation_french, return_tensors="pt")
        ```

    Args:
        vocab_file (`str`, *optional*):
            Path to the vocabulary file.
        tokenizer_file (`str`, *optional*):
            The path to a tokenizer file to use instead of the vocab file.
        bos_token (`str`, *optional*, defaults to `"<s>"`):
            The beginning of sequence token that was used during pretraining. Can be used a sequence classifier token.

            <Tip>

            When building a sequence using special tokens, this is not the token that is used for the beginning of
            sequence. The token used is the `cls_token`.

            </Tip>

        eos_token (`str`, *optional*, defaults to `"</s>"`):
            The end of sequence token.

            <Tip>

            When building a sequence using special tokens, this is not the token that is used for the end of sequence.
            The token used is the `sep_token`.

            </Tip>

        sep_token (`str`, *optional*, defaults to `"</s>"`):
            The separator token, which is used when building a sequence from multiple sequences, e.g. two sequences for
            sequence classification or for a text and a question for question answering. It is also used as the last
            token of a sequence built with special tokens.
        cls_token (`str`, *optional*, defaults to `"<s>"`):
            The classifier token which is used when doing sequence classification (classification of the whole sequence
            instead of per-token classification). It is the first token of the sequence when built with special tokens.
        unk_token (`str`, *optional*, defaults to `"<unk>"`):
            The unknown token. A token that is not in the vocabulary cannot be converted to an ID and is set to be this
            token instead.
        pad_token (`str`, *optional*, defaults to `"<pad>"`):
            The token used for padding, for example when batching sequences of different lengths.
        src_lang (`str`, *optional*, defaults to `"eng"`):
            The language to use as source language for translation.
        tgt_lang (`str`, *optional*, defaults to `"fra"`):
            The language to use as target language for translation.
        additional_special_tokens (tuple or list of `str` or `tokenizers.AddedToken`, *optional*):
            A tuple or a list of additional special tokens.
    """
    vocab_files_names = VOCAB_FILES_NAMES
    pretrained_vocab_files_map = PRETRAINED_VOCAB_FILES_MAP
    max_model_input_sizes = PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES
    slow_tokenizer_class = SeamlessM4TTokenizer
    model_input_names = ["input_ids", "attention_mask"]

    prefix_tokens: List[int] = []
    suffix_tokens: List[int] = []

    def __init__(
        self,
        vocab_file=None,
        tokenizer_file=None,
        bos_token="<s>",
        eos_token="</s>",
        sep_token="</s>",
        cls_token="<s>",
        unk_token="<unk>",
        pad_token="<pad>",
        src_lang="eng",
        tgt_lang="fra",
        additional_special_tokens=None,
        **kwargs,
    ):
        """
        Initializes the SeamlessM4TTokenizerFast class.
        
        Args:
            self: An instance of the SeamlessM4TTokenizerFast class.
            vocab_file (str): Path to the vocabulary file.
            tokenizer_file (str): Path to the tokenizer file.
            bos_token (str): The beginning of sequence token. Defaults to '<s>'.
            eos_token (str): The end of sequence token. Defaults to '</s>'.
            sep_token (str): The separator token. Defaults to '</s>'.
            cls_token (str): The classification token. Defaults to '<s>'.
            unk_token (str): The unknown token. Defaults to '<unk>'.
            pad_token (str): The padding token. Defaults to '<pad>'.
            src_lang (str): The source language. Defaults to 'eng'.
            tgt_lang (str): The target language. Defaults to 'fra'.
            additional_special_tokens (List[str]): A list of additional special tokens. Defaults to None.
        
        Returns:
            None.
        
        Raises:
            None.
        """
        super().__init__(
            vocab_file=vocab_file,
            tokenizer_file=tokenizer_file,
            bos_token=bos_token,
            eos_token=eos_token,
            sep_token=sep_token,
            cls_token=cls_token,
            unk_token=unk_token,
            pad_token=pad_token,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            additional_special_tokens=additional_special_tokens,
            **kwargs,
        )

        self.vocab_file = vocab_file
        self._src_lang = f"__{src_lang}__" if "__" not in src_lang else src_lang
        self._tgt_lang = f"__{tgt_lang}__" if "__" not in tgt_lang else tgt_lang
        self.set_src_lang_special_tokens(self._src_lang)
        self.set_tgt_lang_special_tokens(self._tgt_lang)

    @property
    def can_save_slow_tokenizer(self) -> bool:
        """
        This method checks if the slow tokenizer can be saved.
        
        Args:
            self (SeamlessM4TTokenizerFast): The instance of the SeamlessM4TTokenizerFast class.
            
        Returns:
            bool: Returns True if the vocab_file exists, False otherwise.
            
        Raises:
            None
        """
        return os.path.isfile(self.vocab_file) if self.vocab_file else False

    @property
    # Copied from transformers.models.nllb.tokenization_nllb.NllbTokenizer.src_lang
    def src_lang(self) -> str:
        """
        This method returns the source language used for tokenization.
        
        Args:
            self: An instance of the SeamlessM4TTokenizerFast class.
        
        Returns:
            str: The source language used for tokenization.
        
        Raises:
            No specific exceptions are raised by this method.
        """
        return self._src_lang

    @src_lang.setter
    def src_lang(self, new_src_lang: str) -> None:
        """
        src_lang(self, new_src_lang: str) -> None
        
        This method sets the source language for the SeamlessM4TTokenizerFast object.
        
        Args:
            self: The instance of the SeamlessM4TTokenizerFast class.
            new_src_lang (str): The new source language to be set. It should be a string representing the language code.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            N/A
        """
        if "__" not in new_src_lang:
            self._src_lang = f"__{new_src_lang}__"
        else:
            self._src_lang = new_src_lang
        self.set_src_lang_special_tokens(self._src_lang)

    @property
    def tgt_lang(self) -> str:
        """
        tgt_lang method in the SeamlessM4TTokenizerFast class.
        
        Args:
            self: A reference to the current instance of the class.
        
        Returns:
            str: The language code representing the target language for tokenization.
        
        Raises:
            No specific exceptions are documented to be raised by this method.
        """
        return self._tgt_lang

    @tgt_lang.setter
    def tgt_lang(self, new_tgt_lang: str) -> None:
        """
        Sets the target language for the SeamlessM4TTokenizerFast object.
        
        Args:
            self (SeamlessM4TTokenizerFast): The instance of the SeamlessM4TTokenizerFast class.
            new_tgt_lang (str): The new target language to be set. It should be a string representing the language code.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            None. This method does not raise any exceptions.
        """
        if "__" not in new_tgt_lang:
            self._tgt_lang = f"__{new_tgt_lang}__"
        else:
            self._tgt_lang = new_tgt_lang
        self.set_tgt_lang_special_tokens(self._tgt_lang)

    def build_inputs_with_special_tokens(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Build model inputs from a sequence or a pair of sequence for sequence classification tasks by concatenating and
        adding special tokens. The special tokens depend on calling set_lang.

        An SeamlessM4T sequence has the following format, where `X` represents the sequence:

        >   - `input_ids` (for encoder) `[src_lang_code] X [eos]`
        >   - `decoder_input_ids`: (for decoder) `[eos, tgt_lang_code] X [eos]`

        BOS is never used. Pairs of sequences are not the expected use case, but they will be handled without a
        separator.

        Args:
            token_ids_0 (`List[int]`):
                List of IDs to which the special tokens will be added.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: list of [input IDs](../glossary#input-ids) with the appropriate special tokens.
        """
        if token_ids_1 is None:
            return self.prefix_tokens + token_ids_0 + self.suffix_tokens
        # We don't expect to process pairs, but leave the pair logic for API consistency
        return self.prefix_tokens + token_ids_0 + token_ids_1 + self.suffix_tokens

    # Copied from transformers.models.nllb.tokenization_nllb_fast.NllbTokenizerFast.create_token_type_ids_from_sequences
    def create_token_type_ids_from_sequences(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Create a mask from the two sequences passed to be used in a sequence-pair classification task. nllb does not
        make use of token type ids, therefore a list of zeros is returned.

        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: List of zeros.

        """
        sep = [self.sep_token_id]
        cls = [self.cls_token_id]

        if token_ids_1 is None:
            return len(cls + token_ids_0 + sep) * [0]
        return len(cls + token_ids_0 + sep + sep + token_ids_1 + sep) * [0]

    def _build_translation_inputs(
        self, raw_inputs, return_tensors: str, src_lang: Optional[str], tgt_lang: Optional[str], **extra_kwargs
    ):
        """Used by translation pipeline, to prepare inputs for the generate function"""
        if src_lang is None or tgt_lang is None:
            raise ValueError("Translation requires a `src_lang` and a `tgt_lang` for this model")
        self.src_lang = src_lang
        inputs = self(raw_inputs, add_special_tokens=True, return_tensors=return_tensors, **extra_kwargs)
        if "__" not in tgt_lang:
            tgt_lang = f"__{tgt_lang}__"
        tgt_lang_id = self.convert_tokens_to_ids(tgt_lang)
        inputs["forced_bos_token_id"] = tgt_lang_id
        return inputs

    # Copied from transformers.models.nllb.tokenization_nllb_fast.NllbTokenizerFast.prepare_seq2seq_batch with "fra_Latn"->"fra", "eng_Latn"->"eng"
    def prepare_seq2seq_batch(
        self,
        src_texts: List[str],
        src_lang: str = "eng",
        tgt_texts: Optional[List[str]] = None,
        tgt_lang: str = "fra",
        **kwargs,
    ) -> BatchEncoding:
        """
        Prepares a batch for sequence-to-sequence tokenization using the SeamlessM4TTokenizerFast class.
        
        Args:
            self (SeamlessM4TTokenizerFast): An instance of the SeamlessM4TTokenizerFast class.
            src_texts (List[str]): A list of source texts to be tokenized.
            src_lang (str, optional): The language of the source texts. Defaults to 'eng'.
            tgt_texts (List[str], optional): A list of target texts to be tokenized. Defaults to None.
            tgt_lang (str, optional): The language of the target texts. Defaults to 'fra'.
            **kwargs: Additional keyword arguments that can be passed to the underlying tokenizer.
        
        Returns:
            BatchEncoding: A batch encoding containing the tokenized sequences.
        
        Raises:
            None
        
        This method prepares a batch of source texts and, optionally, target texts for tokenization using the SeamlessM4TTokenizerFast class. It takes the source texts, source language, target texts, and
            target language as input parameters. The method returns a BatchEncoding object, which contains the tokenized sequences.
        
        The 'self' parameter refers to the instance of the SeamlessM4TTokenizerFast class on which the method is called.
        
        The 'src_texts' parameter is a list of source texts that need to be tokenized.
        
        The 'src_lang' parameter specifies the language of the source texts. The default value is 'eng'.
        
        The 'tgt_texts' parameter is an optional list of target texts that need to be tokenized. If not provided, it defaults to None.
        
        The 'tgt_lang' parameter specifies the language of the target texts. The default value is 'fra'.
        
        Additional keyword arguments can be passed using the '**kwargs' parameter. These arguments will be forwarded to the underlying tokenizer.
        
        Example usage:
            ```python
            tokenizer = SeamlessM4TTokenizerFast()
            src_texts = ["Hello, world!", "How are you?"]
            tgt_texts = ["Bonjour, le monde!", "Comment ça va?"]
            batch = tokenizer.prepare_seq2seq_batch(src_texts, src_lang='eng', tgt_texts=tgt_texts, tgt_lang='fra')
            ```
        """
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        return super().prepare_seq2seq_batch(src_texts, tgt_texts, **kwargs)

    # Copied from transformers.models.nllb.tokenization_nllb_fast.NllbTokenizerFast._switch_to_input_mode
    def _switch_to_input_mode(self):
        """
        Method to switch the tokenizer to input mode by setting source language special tokens.
        
        Args:
            self (SeamlessM4TTokenizerFast): The instance of the SeamlessM4TTokenizerFast class.
                Represents the tokenizer object.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            No specific exceptions are raised by this method.
        """
        return self.set_src_lang_special_tokens(self.src_lang)

    # Copied from transformers.models.nllb.tokenization_nllb_fast.NllbTokenizerFast._switch_to_target_mode
    def _switch_to_target_mode(self):
        """
        Switches the tokenizer to target mode for SeamlessM4TTokenizerFast.
        
        Args:
            self: The instance of SeamlessM4TTokenizerFast.
                Type: object
                Purpose: Represents the instance of the SeamlessM4TTokenizerFast class.
                Restrictions: None
        
        Returns:
            None: Indicates that no value is returned from this method.
                Type: None
                Purpose: The method sets the target language special tokens and does not return any value.
        
        Raises:
            None
        """
        return self.set_tgt_lang_special_tokens(self.tgt_lang)

    def set_src_lang_special_tokens(self, src_lang) -> None:
        """Reset the special tokens to the source lang setting.
        Prefix=[src_lang_code], suffix = [eos]
        """
        self.cur_lang_code = self.convert_tokens_to_ids(src_lang)

        if self.cur_lang_code == self.unk_token_id:
            logger.warning_once(
                f"`tgt_lang={src_lang}` has not be found in the `vocabulary`. Behaviour will probably be unexpected because the language token id will be replaced by the unknown token id."
            )

        self.init_kwargs["src_lang"] = src_lang

        self.prefix_tokens = [self.cur_lang_code]
        self.suffix_tokens = [self.eos_token_id]

        prefix_tokens_str = self.convert_ids_to_tokens(self.prefix_tokens)
        suffix_tokens_str = self.convert_ids_to_tokens(self.suffix_tokens)

        self._tokenizer.post_processor = processors.TemplateProcessing(
            single=prefix_tokens_str + ["$A"] + suffix_tokens_str,
            pair=prefix_tokens_str + ["$A", "$B"] + suffix_tokens_str,
            special_tokens=list(zip(prefix_tokens_str + suffix_tokens_str, self.prefix_tokens + self.suffix_tokens)),
        )

    def set_tgt_lang_special_tokens(self, lang: str) -> None:
        """Reset the special tokens to the target lang setting.
        Prefix=[eos, tgt_lang_code] and suffix=[eos].
        """
        self.cur_lang_code = self.convert_tokens_to_ids(lang)

        if self.cur_lang_code == self.unk_token_id:
            logger.warning_once(
                f"`tgt_lang={lang}` has not be found in the `vocabulary`. Behaviour will probably be unexpected because the language token id will be replaced by the unknown token id."
            )

        self.init_kwargs["tgt_lang"] = lang

        self.prefix_tokens = [self.eos_token_id, self.cur_lang_code]
        self.suffix_tokens = [self.eos_token_id]

        prefix_tokens_str = self.convert_ids_to_tokens(self.prefix_tokens)
        suffix_tokens_str = self.convert_ids_to_tokens(self.suffix_tokens)

        self._tokenizer.post_processor = processors.TemplateProcessing(
            single=prefix_tokens_str + ["$A"] + suffix_tokens_str,
            pair=prefix_tokens_str + ["$A", "$B"] + suffix_tokens_str,
            special_tokens=list(zip(prefix_tokens_str + suffix_tokens_str, self.prefix_tokens + self.suffix_tokens)),
        )

    # Copied from transformers.models.nllb.tokenization_nllb_fast.NllbTokenizerFast.save_vocabulary
    def save_vocabulary(self, save_directory: str, filename_prefix: Optional[str] = None) -> Tuple[str]:
        """
        Save the vocabulary for a slow tokenizer.
        
        Args:
            self (SeamlessM4TTokenizerFast): The instance of the class.
            save_directory (str): The directory where the vocabulary will be saved.
            filename_prefix (Optional[str], optional): The prefix to be added to the filename. Defaults to None.
        
        Returns:
            Tuple[str]: A tuple containing the path to the saved vocabulary file.
        
        Raises:
            ValueError: If the fast tokenizer does not have the necessary information to save the vocabulary for a slow tokenizer.
            FileNotFoundError: If the save_directory does not exist.
            IsADirectoryError: If the save_directory is not a directory.
        
        Note:
            The method assumes that the fast tokenizer has the necessary information to save the vocabulary for a slow tokenizer.
        
        Example:
            tokenizer = SeamlessM4TTokenizerFast()
            save_directory = '/path/to/save/directory'
            filename_prefix = 'vocab'
            vocab_file = tokenizer.save_vocabulary(save_directory, filename_prefix)
            # vocab_file is now ('/path/to/save/directory/vocab-file', )
        """
        if not self.can_save_slow_tokenizer:
            raise ValueError(
                "Your fast tokenizer does not have the necessary information to save the vocabulary for a slow "
                "tokenizer."
            )

        if not os.path.isdir(save_directory):
            logger.error(f"Vocabulary path ({save_directory}) should be a directory.")
            return
        out_vocab_file = os.path.join(
            save_directory, (filename_prefix + "-" if filename_prefix else "") + VOCAB_FILES_NAMES["vocab_file"]
        )

        if os.path.abspath(self.vocab_file) != os.path.abspath(out_vocab_file):
            copyfile(self.vocab_file, out_vocab_file)

        return (out_vocab_file,)

    @classmethod
    def _from_pretrained(
        cls,
        resolved_vocab_files,
        pretrained_model_name_or_path,
        init_configuration,
        *init_inputs,
        token=None,
        cache_dir=None,
        local_files_only=False,
        _commit_hash=None,
        _is_local=False,
        **kwargs,
    ):
        """
        Method _from_pretrained in the class SeamlessM4TTokenizerFast.
        
        Args:
            cls (class): The class itself.
            resolved_vocab_files (dict): A dictionary containing resolved vocabulary files.
            pretrained_model_name_or_path (str): The name or path of the pretrained model.
            init_configuration (dict): Initial configuration settings for the tokenizer.
            
        Returns:
            None: This method does not return any value.
            
        Raises:
            N/A
        """
        tokenizer = super()._from_pretrained(
            resolved_vocab_files,
            pretrained_model_name_or_path,
            init_configuration,
            *init_inputs,
            token=token,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
            _commit_hash=_commit_hash,
            _is_local=_is_local,
            **kwargs,
        )

        # ensure also set after from pretrained
        tokenizer.set_src_lang_special_tokens(tokenizer._src_lang)
        tokenizer.set_tgt_lang_special_tokens(tokenizer._tgt_lang)

        return tokenizer

    def __call__(
        self,
        text: Union[TextInput, PreTokenizedInput, List[TextInput], List[PreTokenizedInput]] = None,
        text_pair: Optional[Union[TextInput, PreTokenizedInput, List[TextInput], List[PreTokenizedInput]]] = None,
        text_target: Union[TextInput, PreTokenizedInput, List[TextInput], List[PreTokenizedInput]] = None,
        text_pair_target: Optional[
            Union[TextInput, PreTokenizedInput, List[TextInput], List[PreTokenizedInput]]
        ] = None,
        padding: Union[bool, str, PaddingStrategy] = True,
        pad_to_multiple_of: Optional[int] = 2,
        src_lang: Optional[str] = None,
        tgt_lang: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            text (`str`, `List[str]`, `List[List[str]]`, *optional*):
                The sequence or batch of sequences to be encoded. Each sequence can be a string or a list of strings
                (pretokenized string). If the sequences are provided as list of strings (pretokenized), you must set
                `is_split_into_words=True` (to lift the ambiguity with a batch of sequences).
            text_pair (`str`, `List[str]`, `List[List[str]]`, *optional*):
                The sequence or batch of sequences to be encoded. Each sequence can be a string or a list of strings
                (pretokenized string). If the sequences are provided as list of strings (pretokenized), you must set
                `is_split_into_words=True` (to lift the ambiguity with a batch of sequences).
            text_target (`str`, `List[str]`, `List[List[str]]`, *optional*):
                The sequence or batch of sequences to be encoded as target texts. Each sequence can be a string or a
                list of strings (pretokenized string). If the sequences are provided as list of strings (pretokenized),
                you must set `is_split_into_words=True` (to lift the ambiguity with a batch of sequences).
            text_pair_target (`str`, `List[str]`, `List[List[str]]`, *optional*):
                The sequence or batch of sequences to be encoded as target texts. Each sequence can be a string or a
                list of strings (pretokenized string). If the sequences are provided as list of strings (pretokenized),
                you must set `is_split_into_words=True` (to lift the ambiguity with a batch of sequences).
            padding (`bool`, `str` or [`~utils.PaddingStrategy`], *optional*, defaults to `True`):
                 Select a strategy to pad the returned sequences (according to the model's padding side and padding
                 index) among:
                >   - `True` or `'longest'`: Pad to the longest sequence in the batch (or no padding if only a single
                    sequence if provided).
                >   - `'max_length'`: Pad to a maximum length specified with the argument `max_length` or to the maximum
                    acceptable input length for the model if that argument is not provided.
                >   - `False` or `'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of different
                    lengths).
            pad_to_multiple_of (`int`, *optional*):
                If set will pad the sequence to a multiple of the provided value.

                This is especially useful to enable the use of Tensor Cores on NVIDIA hardware with compute capability
                `>= 7.5` (Volta).
            src_lang (`str`, *optional*):
                A string representing the source language. If not specified, the last `src_lang` specified (either
                during initialization or when calling this tokenizer) will be used.
            tgt_lang (`str`, *optional*):
                A string representing the target language. If not specified, the last `tgt_lang` specified (either
                during initialization or when calling this tokenizer) will be used.
            kwargs (*optional*):
                Remaining dictionary of keyword arguments that will be passed to [`PreTrainedTokenizerFast.__call__`].
        """
        if src_lang is not None:
            self.src_lang = src_lang
        if tgt_lang is not None:
            self.tgt_lang = tgt_lang

        output = super().__call__(
            text=text,
            text_pair=text_pair,
            text_target=text_target,
            text_pair_target=text_pair_target,
            padding=padding,
            pad_to_multiple_of=pad_to_multiple_of,
            **kwargs,
        )

        return output

__all__ = ['SeamlessM4TTokenizerFast']
