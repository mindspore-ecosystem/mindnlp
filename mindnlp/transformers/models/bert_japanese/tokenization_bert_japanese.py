# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors and The HuggingFace Inc. team.
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
"""Tokenization classes."""


import collections
import copy
import os
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from mindnlp.utils import is_sentencepiece_available, is_sudachi_projection_available, logging
from ...tokenization_utils import PreTrainedTokenizer, _is_control, _is_punctuation, _is_whitespace


if is_sentencepiece_available():
    import sentencepiece as spm
else:
    spm = None

logger = logging.get_logger(__name__)

VOCAB_FILES_NAMES = {"vocab_file": "vocab.txt", "spm_file": "spiece.model"}

SPIECE_UNDERLINE = "▁"


# Copied from transformers.models.bert.tokenization_bert.load_vocab
def load_vocab(vocab_file):
    """Loads a vocabulary file into a dictionary."""
    vocab = collections.OrderedDict()
    with open(vocab_file, "r", encoding="utf-8") as reader:
        tokens = reader.readlines()
    for index, token in enumerate(tokens):
        token = token.rstrip("\n")
        vocab[token] = index
    return vocab


# Copied from transformers.models.bert.tokenization_bert.whitespace_tokenize
def whitespace_tokenize(text):
    """Runs basic whitespace cleaning and splitting on a piece of text."""
    text = text.strip()
    if not text:
        return []
    tokens = text.split()
    return tokens


class BertJapaneseTokenizer(PreTrainedTokenizer):
    r"""
    Construct a BERT tokenizer for Japanese text.

    This tokenizer inherits from [`PreTrainedTokenizer`] which contains most of the main methods. Users should refer
    to: this superclass for more information regarding those methods.

    Args:
        vocab_file (`str`):
            Path to a one-wordpiece-per-line vocabulary file.
        spm_file (`str`, *optional*):
            Path to [SentencePiece](https://github.com/google/sentencepiece) file (generally has a .spm or .model
            extension) that contains the vocabulary.
        do_lower_case (`bool`, *optional*, defaults to `True`):
            Whether to lower case the input. Only has an effect when do_basic_tokenize=True.
        do_word_tokenize (`bool`, *optional*, defaults to `True`):
            Whether to do word tokenization.
        do_subword_tokenize (`bool`, *optional*, defaults to `True`):
            Whether to do subword tokenization.
        word_tokenizer_type (`str`, *optional*, defaults to `"basic"`):
            Type of word tokenizer. Choose from ["basic", "mecab", "sudachi", "jumanpp"].
        subword_tokenizer_type (`str`, *optional*, defaults to `"wordpiece"`):
            Type of subword tokenizer. Choose from ["wordpiece", "character", "sentencepiece",].
        mecab_kwargs (`dict`, *optional*):
            Dictionary passed to the `MecabTokenizer` constructor.
        sudachi_kwargs (`dict`, *optional*):
            Dictionary passed to the `SudachiTokenizer` constructor.
        jumanpp_kwargs (`dict`, *optional*):
            Dictionary passed to the `JumanppTokenizer` constructor.
    """

    vocab_files_names = VOCAB_FILES_NAMES

    def __init__(
        self,
        vocab_file,
        spm_file=None,
        do_lower_case=False,
        do_word_tokenize=True,
        do_subword_tokenize=True,
        word_tokenizer_type="basic",
        subword_tokenizer_type="wordpiece",
        never_split=None,
        unk_token="[UNK]",
        sep_token="[SEP]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        mask_token="[MASK]",
        mecab_kwargs=None,
        sudachi_kwargs=None,
        jumanpp_kwargs=None,
        **kwargs,
    ):

        """
        Initializes a new instance of the BertJapaneseTokenizer class.
        
        Args:
            self (object): The instance of the class.
            vocab_file (str): The path to the vocabulary file. If not using a 'sentencepiece' subword tokenizer, this file is required.
            spm_file (str, optional): The path to the SentencePiece model file. Defaults to None.
            do_lower_case (bool): A flag to indicate whether the tokenizer should convert all characters to lowercase. Defaults to False.
            do_word_tokenize (bool): A flag to indicate whether word tokenization should be performed. Defaults to True.
            do_subword_tokenize (bool): A flag to indicate whether subword tokenization should be performed. Defaults to True.
            word_tokenizer_type (str): The type of word tokenizer to use. Must be one of 'basic', 'mecab', 'sudachi', or 'jumanpp'.
            subword_tokenizer_type (str): The type of subword tokenizer to use. Must be one of 'wordpiece', 'character', or 'sentencepiece'.
            never_split (list): A list of tokens that should not be split during tokenization. Defaults to None.
            unk_token (str): The token to represent unknown words. Defaults to '[UNK]'.
            sep_token (str): The separator token. Defaults to '[SEP]'.
            pad_token (str): The padding token. Defaults to '[PAD]'.
            cls_token (str): The classification token. Defaults to '[CLS]'.
            mask_token (str): The mask token. Defaults to '[MASK]'.
            mecab_kwargs (dict): Additional keyword arguments for the Mecab word tokenizer. Defaults to None.
            sudachi_kwargs (dict): Additional keyword arguments for the Sudachi word tokenizer. Defaults to None.
            jumanpp_kwargs (dict): Additional keyword arguments for the Jumanpp word tokenizer. Defaults to None.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            ValueError: If the specified vocabulary or SentencePiece model file cannot be found, or if an invalid tokenizer type is specified.
        """
        if subword_tokenizer_type == "sentencepiece":
            if not os.path.isfile(spm_file):
                raise ValueError(
                    f"Can't find a vocabulary file at path '{spm_file}'. To load the vocabulary from a Google"
                    " pretrained model use `tokenizer = AutoTokenizer.from_pretrained(PRETRAINED_MODEL_NAME)`"
                )
            self.spm_file = spm_file
        else:
            if not os.path.isfile(vocab_file):
                raise ValueError(
                    f"Can't find a vocabulary file at path '{vocab_file}'. To load the vocabulary from a Google"
                    " pretrained model use `tokenizer = AutoTokenizer.from_pretrained(PRETRAINED_MODEL_NAME)`"
                )
            self.vocab = load_vocab(vocab_file)
            self.ids_to_tokens = collections.OrderedDict([(ids, tok) for tok, ids in self.vocab.items()])

        self.do_word_tokenize = do_word_tokenize
        self.word_tokenizer_type = word_tokenizer_type
        self.lower_case = do_lower_case
        self.never_split = never_split
        self.mecab_kwargs = copy.deepcopy(mecab_kwargs)
        self.sudachi_kwargs = copy.deepcopy(sudachi_kwargs)
        self.jumanpp_kwargs = copy.deepcopy(jumanpp_kwargs)
        if do_word_tokenize:
            if word_tokenizer_type == "basic":
                self.word_tokenizer = BasicTokenizer(
                    do_lower_case=do_lower_case, never_split=never_split, tokenize_chinese_chars=False
                )
            elif word_tokenizer_type == "mecab":
                self.word_tokenizer = MecabTokenizer(
                    do_lower_case=do_lower_case, never_split=never_split, **(mecab_kwargs or {})
                )
            elif word_tokenizer_type == "sudachi":
                self.word_tokenizer = SudachiTokenizer(
                    do_lower_case=do_lower_case, never_split=never_split, **(sudachi_kwargs or {})
                )
            elif word_tokenizer_type == "jumanpp":
                self.word_tokenizer = JumanppTokenizer(
                    do_lower_case=do_lower_case, never_split=never_split, **(jumanpp_kwargs or {})
                )
            else:
                raise ValueError(f"Invalid word_tokenizer_type '{word_tokenizer_type}' is specified.")

        self.do_subword_tokenize = do_subword_tokenize
        self.subword_tokenizer_type = subword_tokenizer_type
        if do_subword_tokenize:
            if subword_tokenizer_type == "wordpiece":
                self.subword_tokenizer = WordpieceTokenizer(vocab=self.vocab, unk_token=str(unk_token))
            elif subword_tokenizer_type == "character":
                self.subword_tokenizer = CharacterTokenizer(vocab=self.vocab, unk_token=str(unk_token))
            elif subword_tokenizer_type == "sentencepiece":
                self.subword_tokenizer = SentencepieceTokenizer(vocab=self.spm_file, unk_token=str(unk_token))
            else:
                raise ValueError(f"Invalid subword_tokenizer_type '{subword_tokenizer_type}' is specified.")
        super().__init__(
            spm_file=spm_file,
            unk_token=unk_token,
            sep_token=sep_token,
            pad_token=pad_token,
            cls_token=cls_token,
            mask_token=mask_token,
            do_lower_case=do_lower_case,
            do_word_tokenize=do_word_tokenize,
            do_subword_tokenize=do_subword_tokenize,
            word_tokenizer_type=word_tokenizer_type,
            subword_tokenizer_type=subword_tokenizer_type,
            never_split=never_split,
            mecab_kwargs=mecab_kwargs,
            sudachi_kwargs=sudachi_kwargs,
            jumanpp_kwargs=jumanpp_kwargs,
            **kwargs,
        )

    @property
    def do_lower_case(self):

        """
        Method: do_lower_case
        
        Description:
        This method returns the lower case value of the input.
        
        Args:
        - self: Represents the instance of the class BertJapaneseTokenizer. It is used to access the attributes and methods of the class.
        
        Returns:
        None: This method does not return any value, rather it directly accesses and returns the lower case value of the input.
        
        Raises:
        This method does not raise any exceptions.
        """
        return self.lower_case

    def __getstate__(self):

        """
        This method '__getstate__' is defined within the class 'BertJapaneseTokenizer' and is used to retrieve the internal state of the object for pickling purposes.
        
        Args:
            self: This parameter represents the instance of the 'BertJapaneseTokenizer' class itself. It is required to access the internal attributes of the object.
        
        Returns:
            The method returns a dictionary representing the current state of the object. If the 'word_tokenizer_type' attribute of the object is one of ['mecab', 'sudachi', 'jumanpp'], the 'word_tokenizer' attribute is removed from the state dictionary before returning it.
        
        Raises:
            This method does not raise any exceptions under normal circumstances.
        """
        state = dict(self.__dict__)
        if self.word_tokenizer_type in ["mecab", "sudachi", "jumanpp"]:
            del state["word_tokenizer"]
        return state

    def __setstate__(self, state):

        """
        Args:
            self (BertJapaneseTokenizer): The instance of the BertJapaneseTokenizer class.
            state (dict): The state dictionary containing the attributes to be restored.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            N/A
        """
        self.__dict__ = state
        if self.word_tokenizer_type == "mecab":
            self.word_tokenizer = MecabTokenizer(
                do_lower_case=self.do_lower_case, never_split=self.never_split, **(self.mecab_kwargs or {})
            )
        elif self.word_tokenizer_type == "sudachi":
            self.word_tokenizer = SudachiTokenizer(
                do_lower_case=self.do_lower_case, never_split=self.never_split, **(self.sudachi_kwargs or {})
            )
        elif self.word_tokenizer_type == "jumanpp":
            self.word_tokenizer = JumanppTokenizer(
                do_lower_case=self.do_lower_case, never_split=self.never_split, **(self.jumanpp_kwargs or {})
            )

    def _tokenize(self, text):

        """
        Tokenizes the given text using word and subword tokenization.
        
        Args:
            self (BertJapaneseTokenizer): The instance of the BertJapaneseTokenizer class.
            text (str): The text to be tokenized.
        
        Returns:
            list: The list of tokens after word and subword tokenization.
        
        Raises:
            None.
        
        This method tokenizes the input text using word and subword tokenization techniques. 
        If the 'do_word_tokenize' flag is set to True, the text is first tokenized into words using the 'word_tokenizer' 
        with the 'never_split' option set to 'all_special_tokens'. If the flag is set to False, the text is treated 
        as a single token.
        
        If the 'do_subword_tokenize' flag is set to True, each word token is further split into subword tokens using 
        the 'subword_tokenizer'. The resulting subword tokens are returned as the final list of tokens. If the flag 
        is set to False, the word tokens are returned as is.
        
        Note: The 'do_word_tokenize' and 'do_subword_tokenize' flags are set during the initialization of the 
        BertJapaneseTokenizer class.
        
        Example:
            tokenizer = BertJapaneseTokenizer()
            text = "こんにちは、世界！"
            tokens = tokenizer._tokenize(text)
            print(tokens)
            # Output: ['こんにちは', '、', '世界', '！']
        """
        if self.do_word_tokenize:
            tokens = self.word_tokenizer.tokenize(text, never_split=self.all_special_tokens)
        else:
            tokens = [text]

        if self.do_subword_tokenize:
            split_tokens = [sub_token for token in tokens for sub_token in self.subword_tokenizer.tokenize(token)]
        else:
            split_tokens = tokens

        return split_tokens

    @property
    def vocab_size(self):

        """
        This method 'vocab_size' in the class 'BertJapaneseTokenizer' retrieves the vocabulary size based on the tokenizer type.
        
        Args:
            self (object): The instance of the BertJapaneseTokenizer class.
            
        Returns:
            None: This method does not return any value directly. The vocabulary size is accessed through the property 'vocab_size'.
            
        Raises:
            N/A
        """
        if self.subword_tokenizer_type == "sentencepiece":
            return len(self.subword_tokenizer.sp_model)
        return len(self.vocab)

    def get_vocab(self):

        """
        This method 'get_vocab' in the class 'BertJapaneseTokenizer' retrieves the vocabulary used by the tokenizer.
        
        Args:
            self: The instance of the BertJapaneseTokenizer class. It is a required parameter for instance method access.
        
        Returns:
            Returns a dictionary representing the vocabulary. If the subword_tokenizer_type is 'sentencepiece', the vocabulary is constructed by mapping token IDs to their corresponding tokens for the range of 0 to vocab_size. Any added tokens are then added to this vocabulary. If the subword_tokenizer_type is not 'sentencepiece', the vocabulary is a combination of the existing vocabulary and the added_tokens_encoder.
        
        Raises:
            No specific exceptions are documented to be raised by this method.
        """
        if self.subword_tokenizer_type == "sentencepiece":
            vocab = {self.convert_ids_to_tokens(i): i for i in range(self.vocab_size)}
            vocab.update(self.added_tokens_encoder)
            return vocab
        return dict(self.vocab, **self.added_tokens_encoder)

    def _convert_token_to_id(self, token):
        """Converts a token (str) in an id using the vocab."""
        if self.subword_tokenizer_type == "sentencepiece":
            return self.subword_tokenizer.sp_model.PieceToId(token)
        return self.vocab.get(token, self.vocab.get(self.unk_token))

    def _convert_id_to_token(self, index):
        """Converts an index (integer) in a token (str) using the vocab."""
        if self.subword_tokenizer_type == "sentencepiece":
            return self.subword_tokenizer.sp_model.IdToPiece(index)
        return self.ids_to_tokens.get(index, self.unk_token)

    def convert_tokens_to_string(self, tokens):
        """Converts a sequence of tokens (string) in a single string."""
        if self.subword_tokenizer_type == "sentencepiece":
            return self.subword_tokenizer.sp_model.decode(tokens)
        out_string = " ".join(tokens).replace(" ##", "").strip()
        return out_string

    # Copied from transformers.models.bert.tokenization_bert.BertTokenizer.build_inputs_with_special_tokens
    def build_inputs_with_special_tokens(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Build model inputs from a sequence or a pair of sequence for sequence classification tasks by concatenating and
        adding special tokens. A BERT sequence has the following format:

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
        if token_ids_1 is None:
            return [self.cls_token_id] + token_ids_0 + [self.sep_token_id]
        cls = [self.cls_token_id]
        sep = [self.sep_token_id]
        return cls + token_ids_0 + sep + token_ids_1 + sep

    # Copied from transformers.models.bert.tokenization_bert.BertTokenizer.get_special_tokens_mask
    def get_special_tokens_mask(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None, already_has_special_tokens: bool = False
    ) -> List[int]:
        """
        Retrieve sequence ids from a token list that has no special tokens added. This method is called when adding
        special tokens using the tokenizer `prepare_for_model` method.

        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.
            already_has_special_tokens (`bool`, *optional*, defaults to `False`):
                Whether or not the token list is already formatted with special tokens for the model.

        Returns:
            `List[int]`: A list of integers in the range [0, 1]: 1 for a special token, 0 for a sequence token.
        """

        if already_has_special_tokens:
            return super().get_special_tokens_mask(
                token_ids_0=token_ids_0, token_ids_1=token_ids_1, already_has_special_tokens=True
            )

        if token_ids_1 is not None:
            return [1] + ([0] * len(token_ids_0)) + [1] + ([0] * len(token_ids_1)) + [1]
        return [1] + ([0] * len(token_ids_0)) + [1]

    # Copied from transformers.models.bert.tokenization_bert.BertTokenizer.create_token_type_ids_from_sequences
    def create_token_type_ids_from_sequences(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Create a mask from the two sequences passed to be used in a sequence-pair classification task. A BERT sequence
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
        Save the vocabulary to a file in the specified directory.
        
        Args:
            self: Instance of the BertJapaneseTokenizer class.
            save_directory (str): The directory where the vocabulary file will be saved.
            filename_prefix (Optional[str]): Optional prefix to be added to the filename. Defaults to None.
        
        Returns:
            Tuple[str]: A tuple containing the path to the saved vocabulary file.
        
        Raises:
            FileNotFoundError: If the specified save_directory does not exist.
            ValueError: If the subword_tokenizer_type is not supported.
            IOError: If there is an issue writing the vocabulary file to the specified location.
        """
        if os.path.isdir(save_directory):
            if self.subword_tokenizer_type == "sentencepiece":
                vocab_file = os.path.join(
                    save_directory, (filename_prefix + "-" if filename_prefix else "") + VOCAB_FILES_NAMES["spm_file"]
                )
            else:
                vocab_file = os.path.join(
                    save_directory,
                    (filename_prefix + "-" if filename_prefix else "") + VOCAB_FILES_NAMES["vocab_file"],
                )
        else:
            vocab_file = (filename_prefix + "-" if filename_prefix else "") + save_directory

        if self.subword_tokenizer_type == "sentencepiece":
            with open(vocab_file, "wb") as writer:
                content_spiece_model = self.subword_tokenizer.sp_model.serialized_model_proto()
                writer.write(content_spiece_model)
        else:
            with open(vocab_file, "w", encoding="utf-8") as writer:
                index = 0
                for token, token_index in sorted(self.vocab.items(), key=lambda kv: kv[1]):
                    if index != token_index:
                        logger.warning(
                            f"Saving vocabulary to {vocab_file}: vocabulary indices are not consecutive."
                            " Please check that the vocabulary is not corrupted!"
                        )
                        index = token_index
                    writer.write(token + "\n")
                    index += 1
        return (vocab_file,)


class MecabTokenizer:
    """Runs basic tokenization with MeCab morphological parser."""

    def __init__(
        self,
        do_lower_case=False,
        never_split=None,
        normalize_text=True,
        mecab_dic: Optional[str] = "ipadic",
        mecab_option: Optional[str] = None,
    ):
        """
        Constructs a MecabTokenizer.

        Args:
            **do_lower_case**: (*optional*) boolean (default True)
                Whether to lowercase the input.
            **never_split**: (*optional*) list of str
                Kept for backward compatibility purposes. Now implemented directly at the base class level (see
                [`PreTrainedTokenizer.tokenize`]) List of tokens not to split.
            **normalize_text**: (*optional*) boolean (default True)
                Whether to apply unicode normalization to text before tokenization.
            **mecab_dic**: (*optional*) string (default "ipadic")
                Name of dictionary to be used for MeCab initialization. If you are using a system-installed dictionary,
                set this option to `None` and modify *mecab_option*.
            **mecab_option**: (*optional*) string
                String passed to MeCab constructor.
        """
        self.do_lower_case = do_lower_case
        self.never_split = never_split if never_split is not None else []
        self.normalize_text = normalize_text

        try:
            import fugashi
        except ModuleNotFoundError as error:
            raise error.__class__(
                "You need to install fugashi to use MecabTokenizer. "
                "See https://pypi.org/project/fugashi/ for installation."
            )

        mecab_option = mecab_option or ""

        if mecab_dic is not None:
            if mecab_dic == "ipadic":
                try:
                    import ipadic
                except ModuleNotFoundError as error:
                    raise error.__class__(
                        "The ipadic dictionary is not installed. "
                        "See https://github.com/polm/ipadic-py for installation."
                    )

                dic_dir = ipadic.DICDIR

            elif mecab_dic == "unidic_lite":
                try:
                    import unidic_lite
                except ModuleNotFoundError as error:
                    raise error.__class__(
                        "The unidic_lite dictionary is not installed. "
                        "See https://github.com/polm/unidic-lite for installation."
                    )

                dic_dir = unidic_lite.DICDIR

            elif mecab_dic == "unidic":
                try:
                    import unidic
                except ModuleNotFoundError as error:
                    raise error.__class__(
                        "The unidic dictionary is not installed. "
                        "See https://github.com/polm/unidic-py for installation."
                    )

                dic_dir = unidic.DICDIR
                if not os.path.isdir(dic_dir):
                    raise RuntimeError(
                        "The unidic dictionary itself is not found. "
                        "See https://github.com/polm/unidic-py for installation."
                    )

            else:
                raise ValueError("Invalid mecab_dic is specified.")

            mecabrc = os.path.join(dic_dir, "mecabrc")
            mecab_option = f'-d "{dic_dir}" -r "{mecabrc}" ' + mecab_option

        self.mecab = fugashi.GenericTagger(mecab_option)

    def tokenize(self, text, never_split=None, **kwargs):
        """Tokenizes a piece of text."""
        if self.normalize_text:
            text = unicodedata.normalize("NFKC", text)

        never_split = self.never_split + (never_split if never_split is not None else [])
        tokens = []

        for word in self.mecab(text):
            token = word.surface

            if self.do_lower_case and token not in never_split:
                token = token.lower()

            tokens.append(token)

        return tokens


class SudachiTokenizer:
    """Runs basic tokenization with Sudachi morphological parser."""

    def __init__(
        self,
        do_lower_case=False,
        never_split=None,
        normalize_text=True,
        trim_whitespace=False,
        sudachi_split_mode="A",
        sudachi_config_path=None,
        sudachi_resource_dir=None,
        sudachi_dict_type="core",
        sudachi_projection=None,
    ):
        """
        Constructs a SudachiTokenizer.

        Args:
            **do_lower_case**: (*optional*) boolean (default True)
                Whether to lowercase the input.
            **never_split**: (*optional*) list of str
                Kept for backward compatibility purposes. Now implemented directly at the base class level (see
                [`PreTrainedTokenizer.tokenize`]) List of tokens not to split.
            **normalize_text**: (*optional*) boolean (default True)
                Whether to apply unicode normalization to text before tokenization.
            **trim_whitespace**: (*optional*) boolean (default False)
                Whether to trim all whitespace, tab, newline from tokens.
            **sudachi_split_mode**: (*optional*) string
                Split mode of sudachi, choose from `["A", "B", "C"]`.
            **sudachi_config_path**: (*optional*) string
            **sudachi_resource_dir**: (*optional*) string
            **sudachi_dict_type**: (*optional*) string
                dict type of sudachi, choose from `["small", "core", "full"]`.
            **sudachi_projection**: (*optional*) string
                Word projection mode of sudachi, choose from `["surface", "normalized", "reading", "dictionary", "dictionary_and_surface", "normalized_and_surface", "normalized_nouns"]`.
        """

        self.do_lower_case = do_lower_case
        self.never_split = never_split if never_split is not None else []
        self.normalize_text = normalize_text
        self.trim_whitespace = trim_whitespace

        try:
            from sudachipy import dictionary, tokenizer
        except ImportError:
            raise ImportError(
                "You need to install sudachipy to use SudachiTokenizer. "
                "See https://github.com/WorksApplications/SudachiPy for installation."
            )

        if sudachi_split_mode == "A":
            self.split_mode = tokenizer.Tokenizer.SplitMode.A
        elif sudachi_split_mode == "B":
            self.split_mode = tokenizer.Tokenizer.SplitMode.B
        elif sudachi_split_mode == "C":
            self.split_mode = tokenizer.Tokenizer.SplitMode.C
        else:
            raise ValueError("Invalid sudachi_split_mode is specified.")

        self.projection = sudachi_projection

        sudachi_dictionary = dictionary.Dictionary(
            config_path=sudachi_config_path, resource_dir=sudachi_resource_dir, dict=sudachi_dict_type
        )
        if is_sudachi_projection_available():
            self.sudachi = sudachi_dictionary.create(self.split_mode, projection=self.projection)
        elif self.projection is not None:
            raise ImportError("You need to install sudachipy>=0.6.8 to specify `projection` field in sudachi_kwargs.")
        else:
            self.sudachi = sudachi_dictionary.create(self.split_mode)

    def tokenize(self, text, never_split=None, **kwargs):
        """Tokenizes a piece of text."""
        if self.normalize_text:
            text = unicodedata.normalize("NFKC", text)

        never_split = self.never_split + (never_split if never_split is not None else [])
        tokens = []

        for word in self.sudachi.tokenize(text):
            token = word.surface()

            if self.do_lower_case and token not in never_split:
                token = token.lower()

            if self.trim_whitespace:
                if token.strip() == "":
                    continue
                token = token.strip()

            tokens.append(token)

        return tokens


class JumanppTokenizer:
    """Runs basic tokenization with jumanpp morphological parser."""

    def __init__(
        self,
        do_lower_case=False,
        never_split=None,
        normalize_text=True,
        trim_whitespace=False,
    ):
        """
        Constructs a JumanppTokenizer.

        Args:
            **do_lower_case**: (*optional*) boolean (default True)
                Whether to lowercase the input.
            **never_split**: (*optional*) list of str
                Kept for backward compatibility purposes. Now implemented directly at the base class level (see
                [`PreTrainedTokenizer.tokenize`]) List of tokens not to split.
            **normalize_text**: (*optional*) boolean (default True)
                Whether to apply unicode normalization to text before tokenization.
            **trim_whitespace**: (*optional*) boolean (default False)
                Whether to trim all whitespace, tab, newline from tokens.
        """

        self.do_lower_case = do_lower_case
        self.never_split = never_split if never_split is not None else []
        self.normalize_text = normalize_text
        self.trim_whitespace = trim_whitespace

        try:
            import rhoknp
        except ImportError:
            raise ImportError(
                "You need to install rhoknp to use JumanppTokenizer. "
                "See https://github.com/ku-nlp/rhoknp for installation."
            )

        self.juman = rhoknp.Jumanpp()

    def tokenize(self, text, never_split=None, **kwargs):
        """Tokenizes a piece of text."""
        if self.normalize_text:
            text = unicodedata.normalize("NFKC", text)

        text = text.strip()

        never_split = self.never_split + (never_split if never_split is not None else [])
        tokens = []

        for mrph in self.juman.apply_to_sentence(text).morphemes:
            token = mrph.text

            if self.do_lower_case and token not in never_split:
                token = token.lower()

            if self.trim_whitespace:
                if token.strip() == "":
                    continue
                token = token.strip()

            tokens.append(token)

        return tokens


class CharacterTokenizer:
    """Runs Character tokenization."""

    def __init__(self, vocab, unk_token, normalize_text=True):
        """
        Constructs a CharacterTokenizer.

        Args:
            **vocab**:
                Vocabulary object.
            **unk_token**: str
                A special symbol for out-of-vocabulary token.
            **normalize_text**: (`optional`) boolean (default True)
                Whether to apply unicode normalization to text before tokenization.
        """
        self.vocab = vocab
        self.unk_token = unk_token
        self.normalize_text = normalize_text

    def tokenize(self, text):
        """
        Tokenizes a piece of text into characters.

        For example, `input = "apple""` wil return as output `["a", "p", "p", "l", "e"]`.

        Args:
            text: A single token or whitespace separated tokens.
                This should have already been passed through *BasicTokenizer*.

        Returns:
            A list of characters.
        """
        if self.normalize_text:
            text = unicodedata.normalize("NFKC", text)

        output_tokens = []
        for char in text:
            if char not in self.vocab:
                output_tokens.append(self.unk_token)
                continue

            output_tokens.append(char)

        return output_tokens


# Copied from transformers.models.bert.tokenization_bert.BasicTokenizer
class BasicTokenizer:
    """
    Constructs a BasicTokenizer that will run basic tokenization (punctuation splitting, lower casing, etc.).

    Args:
        do_lower_case (`bool`, *optional*, defaults to `True`):
            Whether or not to lowercase the input when tokenizing.
        never_split (`Iterable`, *optional*):
            Collection of tokens which will never be split during tokenization. Only has an effect when
            `do_basic_tokenize=True`
        tokenize_chinese_chars (`bool`, *optional*, defaults to `True`):
            Whether or not to tokenize Chinese characters.

            This should likely be deactivated for Japanese (see this
            [issue](https://github.com/huggingface/transformers/issues/328)).
        strip_accents (`bool`, *optional*):
            Whether or not to strip all accents. If this option is not specified, then it will be determined by the
            value for `lowercase` (as in the original BERT).
        do_split_on_punc (`bool`, *optional*, defaults to `True`):
            In some instances we want to skip the basic punctuation splitting so that later tokenization can capture
            the full context of the words, such as contractions.
    """

    def __init__(
        self,
        do_lower_case=True,
        never_split=None,
        tokenize_chinese_chars=True,
        strip_accents=None,
        do_split_on_punc=True,
    ):

        '''
        Initializes the BasicTokenizer class with the specified parameters.
        
        Args:
            self: The instance of the class.
            do_lower_case (bool): A flag indicating whether to convert tokens to lower case. Default is True.
            never_split (list): A list of tokens that should never be split. Default is an empty list.
            tokenize_chinese_chars (bool): A flag indicating whether to tokenize Chinese characters. Default is True.
            strip_accents (None): Not used in the current implementation.
            do_split_on_punc (bool): A flag indicating whether to split on punctuation. Default is True.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            None
        '''
        if never_split is None:
            never_split = []
        self.do_lower_case = do_lower_case
        self.never_split = set(never_split)
        self.tokenize_chinese_chars = tokenize_chinese_chars
        self.strip_accents = strip_accents
        self.do_split_on_punc = do_split_on_punc

    def tokenize(self, text, never_split=None):
        """
        Basic Tokenization of a piece of text. For sub-word tokenization, see WordPieceTokenizer.

        Args:
            never_split (`List[str]`, *optional*)
                Kept for backward compatibility purposes. Now implemented directly at the base class level (see
                [`PreTrainedTokenizer.tokenize`]) List of token not to split.
        """
        # union() returns a new set by concatenating the two sets.
        never_split = self.never_split.union(set(never_split)) if never_split else self.never_split
        text = self._clean_text(text)

        # This was added on November 1st, 2018 for the multilingual and Chinese
        # models. This is also applied to the English models now, but it doesn't
        # matter since the English models were not trained on any Chinese data
        # and generally don't have any Chinese data in them (there are Chinese
        # characters in the vocabulary because Wikipedia does have some Chinese
        # words in the English Wikipedia.).
        if self.tokenize_chinese_chars:
            text = self._tokenize_chinese_chars(text)
        # prevents treating the same character with different unicode codepoints as different characters
        unicode_normalized_text = unicodedata.normalize("NFC", text)
        orig_tokens = whitespace_tokenize(unicode_normalized_text)
        split_tokens = []
        for token in orig_tokens:
            if token not in never_split:
                if self.do_lower_case:
                    token = token.lower()
                    if self.strip_accents is not False:
                        token = self._run_strip_accents(token)
                elif self.strip_accents:
                    token = self._run_strip_accents(token)
            split_tokens.extend(self._run_split_on_punc(token, never_split))

        output_tokens = whitespace_tokenize(" ".join(split_tokens))
        return output_tokens

    def _run_strip_accents(self, text):
        """Strips accents from a piece of text."""
        text = unicodedata.normalize("NFD", text)
        output = []
        for char in text:
            cat = unicodedata.category(char)
            if cat == "Mn":
                continue
            output.append(char)
        return "".join(output)

    def _run_split_on_punc(self, text, never_split=None):
        """Splits punctuation on a piece of text."""
        if not self.do_split_on_punc or (never_split is not None and text in never_split):
            return [text]
        chars = list(text)
        i = 0
        start_new_word = True
        output = []
        while i < len(chars):
            char = chars[i]
            if _is_punctuation(char):
                output.append([char])
                start_new_word = True
            else:
                if start_new_word:
                    output.append([])
                start_new_word = False
                output[-1].append(char)
            i += 1

        return ["".join(x) for x in output]

    def _tokenize_chinese_chars(self, text):
        """Adds whitespace around any CJK character."""
        output = []
        for char in text:
            cp = ord(char)
            if self._is_chinese_char(cp):
                output.append(" ")
                output.append(char)
                output.append(" ")
            else:
                output.append(char)
        return "".join(output)

    def _is_chinese_char(self, cp):
        """Checks whether CP is the codepoint of a CJK character."""
        # This defines a "chinese character" as anything in the CJK Unicode block:
        #   https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)
        #
        # Note that the CJK Unicode block is NOT all Japanese and Korean characters,
        # despite its name. The modern Korean Hangul alphabet is a different block,
        # as is Japanese Hiragana and Katakana. Those alphabets are used to write
        # space-separated words, so they are not treated specially and handled
        # like the all of the other languages.
        if (
            (cp >= 0x4E00 and cp <= 0x9FFF)
            or (cp >= 0x3400 and cp <= 0x4DBF)  #
            or (cp >= 0x20000 and cp <= 0x2A6DF)  #
            or (cp >= 0x2A700 and cp <= 0x2B73F)  #
            or (cp >= 0x2B740 and cp <= 0x2B81F)  #
            or (cp >= 0x2B820 and cp <= 0x2CEAF)  #
            or (cp >= 0xF900 and cp <= 0xFAFF)
            or (cp >= 0x2F800 and cp <= 0x2FA1F)  #
        ):  #
            return True

        return False

    def _clean_text(self, text):
        """Performs invalid character removal and whitespace cleanup on text."""
        output = []
        for char in text:
            cp = ord(char)
            if cp == 0 or cp == 0xFFFD or _is_control(char):
                continue
            if _is_whitespace(char):
                output.append(" ")
            else:
                output.append(char)
        return "".join(output)


# Copied from transformers.models.bert.tokenization_bert.WordpieceTokenizer
class WordpieceTokenizer:
    """Runs WordPiece tokenization."""

    def __init__(self, vocab, unk_token, max_input_chars_per_word=100):

        """
        Initializes a new instance of the WordpieceTokenizer class.
        
        Args:
            self (WordpieceTokenizer): The instance of the WordpieceTokenizer class.
            vocab (dict): A dictionary containing the vocabulary for tokenization.
            unk_token (str): The token to be used for unknown or out-of-vocabulary words.
            max_input_chars_per_word (int, optional): The maximum number of characters allowed per word for tokenization. Defaults to 100.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            ValueError: If max_input_chars_per_word is less than or equal to 0.
            TypeError: If vocab is not a dictionary or unk_token is not a string.
        """
        self.vocab = vocab
        self.unk_token = unk_token
        self.max_input_chars_per_word = max_input_chars_per_word

    def tokenize(self, text):
        """
        Tokenizes a piece of text into its word pieces. This uses a greedy longest-match-first algorithm to perform
        tokenization using the given vocabulary.

        For example, `input = "unaffable"` wil return as output `["un", "##aff", "##able"]`.

        Args:
            text: A single token or whitespace separated tokens. This should have
                already been passed through *BasicTokenizer*.

        Returns:
            A list of wordpiece tokens.
        """

        output_tokens = []
        for token in whitespace_tokenize(text):
            chars = list(token)
            if len(chars) > self.max_input_chars_per_word:
                output_tokens.append(self.unk_token)
                continue

            is_bad = False
            start = 0
            sub_tokens = []
            while start < len(chars):
                end = len(chars)
                cur_substr = None
                while start < end:
                    substr = "".join(chars[start:end])
                    if start > 0:
                        substr = "##" + substr
                    if substr in self.vocab:
                        cur_substr = substr
                        break
                    end -= 1
                if cur_substr is None:
                    is_bad = True
                    break
                sub_tokens.append(cur_substr)
                start = end

            if is_bad:
                output_tokens.append(self.unk_token)
            else:
                output_tokens.extend(sub_tokens)
        return output_tokens


class SentencepieceTokenizer:
    """
    Runs sentencepiece tokenization. Based on transformers.models.albert.tokenization_albert.AlbertTokenizer.
    """

    def __init__(
        self,
        vocab,
        unk_token,
        do_lower_case=False,
        remove_space=True,
        keep_accents=True,
        sp_model_kwargs: Optional[Dict[str, Any]] = None,
    ):

        """
        Initializes a SentencepieceTokenizer instance.
        
        Args:
            self: The instance of the class.
            vocab (str): The path to the vocabulary file.
            unk_token (str): The unknown token to be used for out-of-vocabulary tokens.
            do_lower_case (bool, optional): Whether to convert all input to lowercase. Default is False.
            remove_space (bool, optional): Whether to remove space in the tokenization. Default is True.
            keep_accents (bool, optional): Whether to keep accents in the tokenization. Default is True.
            sp_model_kwargs (Optional[Dict[str, Any]], optional): Additional keyword arguments to be passed to the SentencePieceProcessor. Default is None.
        
        Returns:
            None. This method initializes the SentencepieceTokenizer instance.
        
        Raises:
            ValueError: If the vocab file is invalid or missing.
            FileNotFoundError: If the vocab file is not found.
            OSError: If there is an issue loading the SentencePiece model.
        """
        self.vocab = vocab
        self.unk_token = unk_token
        self.do_lower_case = do_lower_case
        self.remove_space = remove_space
        self.keep_accents = keep_accents

        self.sp_model_kwargs = {} if sp_model_kwargs is None else sp_model_kwargs
        self.sp_model = spm.SentencePieceProcessor(**self.sp_model_kwargs)
        self.sp_model.Load(self.vocab)

    def preprocess_text(self, inputs):

        """
        Preprocesses the input text by removing spaces, normalizing accents, and converting to lowercase, if specified.
        
        Args:
            self: An instance of the SentencepieceTokenizer class.
            inputs (str): The input text to be preprocessed.
        
        Returns:
            None: This method modifies the input text in-place.
        
        Raises:
            None: This method does not raise any exceptions.
        """
        if self.remove_space:
            outputs = " ".join(inputs.strip().split())
        else:
            outputs = inputs
        outputs = outputs.replace("``", '"').replace("''", '"')

        if not self.keep_accents:
            outputs = unicodedata.normalize("NFKD", outputs)
            outputs = "".join([c for c in outputs if not unicodedata.combining(c)])
        if self.do_lower_case:
            outputs = outputs.lower()

        return outputs

    def tokenize(self, text):
        """
        Tokenizes text by sentencepiece. Based on [SentencePiece](https://github.com/google/sentencepiece).
        Tokenization needs the given vocabulary.

        Args:
            text: A string needs to be tokenized.

        Returns:
            A list of sentencepiece tokens.
        """
        text = self.preprocess_text(text)
        pieces = self.sp_model.encode(text, out_type=str)
        new_pieces = []
        for piece in pieces:
            if len(piece) > 1 and piece[-1] == str(",") and piece[-2].isdigit():
                cur_pieces = self.sp_model.EncodeAsPieces(piece[:-1].replace(SPIECE_UNDERLINE, ""))
                if piece[0] != SPIECE_UNDERLINE and cur_pieces[0][0] == SPIECE_UNDERLINE:
                    if len(cur_pieces[0]) == 1:
                        cur_pieces = cur_pieces[1:]
                    else:
                        cur_pieces[0] = cur_pieces[0][1:]
                cur_pieces.append(piece[-1])
                new_pieces.extend(cur_pieces)
            else:
                new_pieces.append(piece)

        return new_pieces

__all__ = ['BertJapaneseTokenizer']
