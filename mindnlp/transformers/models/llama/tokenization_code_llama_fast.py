# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team.
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
"""Fast Tokenization classes for Code LLaMA."""
import os
from shutil import copyfile
from typing import List, Optional, Tuple

from tokenizers import normalizers, processors

from mindnlp.utils import is_sentencepiece_available, logging
from ...tokenization_utils_fast import PreTrainedTokenizerFast

if is_sentencepiece_available():
    from .tokenization_code_llama import CodeLlamaTokenizer
else:
    CodeLlamaTokenizer = None

logger = logging.get_logger(__name__)
VOCAB_FILES_NAMES = {"vocab_file": "tokenizer.model", "tokenizer_file": "tokenizer.json"}

SPIECE_UNDERLINE = "▁"


B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"

# fmt: off
DEFAULT_SYSTEM_PROMPT = """You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your \
answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure\
 that your responses are socially unbiased and positive in nature.

If a question does not make any sense, or is not factually coherent, explain why instead of answering something not \
correct. If you don't know the answer to a question, please don't share false information."""
# fmt: on


class CodeLlamaTokenizerFast(PreTrainedTokenizerFast):
    """
    Construct a Llama tokenizer. Based on byte-level Byte-Pair-Encoding.

    This uses notably ByteFallback and no normalization.

    ```python
    >>> from transformers import CodeLlamaTokenizerFast

    >>> tokenizer = CodeLlamaTokenizerFast.from_pretrained("hf-internal-testing/llama-tokenizer")
    >>> tokenizer.encode("Hello this is a test")
    [1, 15043, 445, 338, 263, 1243]
    ```

    If you want to change the `bos_token` or the `eos_token`, make sure to specify them when initializing the model, or
    call `tokenizer.update_post_processor()` to make sure that the post-processing is correctly done (otherwise the
    values of the first token and final token of an encoded sequence will not be correct). For more details, checkout
    [post-processors] (https://hf-mirror.com/docs/tokenizers/api/post-processors) documentation.


    This tokenizer inherits from [`PreTrainedTokenizerFast`] which contains most of the main methods. Users should
    refer to this superclass for more information regarding those methods. The default configuration match that of
    [codellama/CodeLlama-7b-Instruct-hf](https://hf-mirror.com/codellama/CodeLlama-7b-Instruct-hf/blob/main/tokenizer_config.json)
    which supports prompt infilling.

    Args:
        vocab_file (`str`, *optional*):
            [SentencePiece](https://github.com/google/sentencepiece) file (generally has a .model extension) that
            contains the vocabulary necessary to instantiate a tokenizer.
        tokenizer_file (`str`, *optional*):
            [tokenizers](https://github.com/huggingface/tokenizers) file (generally has a .json extension) that
            contains everything needed to load the tokenizer.
        clean_up_tokenization_spaces (`str`, *optional*, defaults to `False`):
            Wether to cleanup spaces after decoding, cleanup consists in removing potential artifacts like extra
            spaces.
        unk_token (`str`, *optional*, defaults to `"<unk>"`):
            The unknown token. A token that is not in the vocabulary cannot be converted to an ID and is set to be this
            token instead.
        bos_token (`str`, *optional*, defaults to `"<s>"`):
            The beginning of sequence token that was used during pretraining. Can be used a sequence classifier token.
        eos_token (`str`, *optional*, defaults to `"</s>"`):
            The end of sequence token.
        prefix_token (`str`, *optional*, defaults to `"▁<PRE>"`):
            Prefix token used for infilling.
        middle_token (`str`, *optional*, defaults to `"▁<MID>"`):
            Middle token used for infilling.
        suffix_token (`str`, *optional*, defaults to `"▁<SUF>"`):
            Suffix token used for infilling.
        eot_token (`str`, *optional*, defaults to `"▁<EOT>"`):
            End of text token used for infilling.
        fill_token (`str`, *optional*, defaults to `"<FILL_ME>"`):
            The token used to split the input between the prefix and suffix.
        additional_special_tokens (`List[str]`, *optional*):
            Additional special tokens used by the tokenizer.
        add_bos_token (`bool`, *optional*, defaults to `True`):
            Whether to add a beginning of sequence token at the start of sequences.
        add_eos_token (`bool`, *optional*, defaults to `False`):
            Whether to add an end of sequence token at the end of sequences.
        use_default_system_prompt (`bool`, *optional*, defaults to `False`):
            Whether or not the default system prompt for Llama should be used.
    """

    vocab_files_names = VOCAB_FILES_NAMES
    slow_tokenizer_class = CodeLlamaTokenizer
    padding_side = "left"
    model_input_names = ["input_ids", "attention_mask"]

    def __init__(
        self,
        vocab_file=None,
        tokenizer_file=None,
        clean_up_tokenization_spaces=False,
        unk_token="<unk>",
        bos_token="<s>",
        eos_token="</s>",
        prefix_token="▁<PRE>",
        middle_token="▁<MID>",
        suffix_token="▁<SUF>",
        eot_token="▁<EOT>",
        fill_token="<FILL_ME>",
        additional_special_tokens=None,
        add_bos_token=True,
        add_eos_token=False,
        use_default_system_prompt=False,
        **kwargs,
    ):

        """
        Initializes an instance of the CodeLlamaTokenizerFast class.
        
        Args:
            self: The instance of the class.
            vocab_file (str, optional): Path to the vocabulary file. Defaults to None.
            tokenizer_file (str, optional): Path to the tokenizer file. Defaults to None.
            clean_up_tokenization_spaces (bool, optional): Whether to clean up tokenization spaces. Defaults to False.
            unk_token (str, optional): Unknown token. Defaults to '<unk>'.
            bos_token (str, optional): Beginning of sentence token. Defaults to '<s>'.
            eos_token (str, optional): End of sentence token. Defaults to '</s>'.
            prefix_token (str, optional): Prefix token. Defaults to '▁<PRE>'.
            middle_token (str, optional): Middle token. Defaults to '▁<MID>'.
            suffix_token (str, optional): Suffix token. Defaults to '▁<SUF>'.
            eot_token (str, optional): End of text token. Defaults to '▁<EOT>'.
            fill_token (str, optional): Fill token. Defaults to '<FILL_ME>'.
            additional_special_tokens (List[str], optional): Additional special tokens. Defaults to None.
            add_bos_token (bool, optional): Whether to add the beginning of sentence token. Defaults to True.
            add_eos_token (bool, optional): Whether to add the end of sentence token. Defaults to False.
            use_default_system_prompt (bool, optional): Whether to use the default system prompt. Defaults to False.
            **kwargs: Additional keyword arguments.
        
        Returns:
            None
        
        Raises:
            None
        """
        # mark tokens special to skip them
        additional_special_tokens = additional_special_tokens or []
        for token in [prefix_token, middle_token, suffix_token, eot_token]:
            additional_special_tokens += [token] if token is not None else []
        self.use_default_system_prompt = use_default_system_prompt

        super().__init__(
            vocab_file=vocab_file,
            tokenizer_file=tokenizer_file,
            clean_up_tokenization_spaces=clean_up_tokenization_spaces,
            additional_special_tokens=additional_special_tokens,
            unk_token=unk_token,
            bos_token=bos_token,
            eos_token=eos_token,
            add_bos_token=add_bos_token,
            add_eos_token=add_eos_token,
            prefix_token=prefix_token,
            middle_token=middle_token,
            suffix_token=suffix_token,
            eot_token=eot_token,
            fill_token=fill_token,
            use_default_system_prompt=use_default_system_prompt,
            **kwargs,
        )
        self._add_bos_token = add_bos_token
        self._add_eos_token = add_eos_token
        self.update_post_processor()

        self.vocab_file = vocab_file

        self._prefix_token = prefix_token
        self._middle_token = middle_token
        self._suffix_token = suffix_token
        self._eot_token = eot_token
        self.fill_token = fill_token

    @property
    def can_save_slow_tokenizer(self) -> bool:

        """
        Checks if the slow tokenizer can be saved.
        
        Args:
            self (CodeLlamaTokenizerFast): An instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            bool: True if the slow tokenizer can be saved, False otherwise.
        
        Raises:
            None.
        
        This method checks if the slow tokenizer can be saved by verifying if the vocab_file attribute exists. 
        If the vocab_file attribute is not None and it corresponds to an existing file, the method returns True. 
        Otherwise, it returns False.
        """
        return os.path.isfile(self.vocab_file) if self.vocab_file else False

    # Copied from transformers.models.llama.tokenization_llama_fast.LlamaTokenizerFast.update_post_processor
    def update_post_processor(self):
        """
        Updates the underlying post processor with the current `bos_token` and `eos_token`.
        """
        bos = self.bos_token
        bos_token_id = self.bos_token_id
        if bos is None and self.add_bos_token:
            raise ValueError("add_bos_token = True but bos_token = None")

        eos = self.eos_token
        eos_token_id = self.eos_token_id
        if eos is None and self.add_eos_token:
            raise ValueError("add_eos_token = True but eos_token = None")

        single = f"{(bos+':0 ') if self.add_bos_token else ''}$A:0{(' '+eos+':0') if self.add_eos_token else ''}"
        pair = f"{single}{(' '+bos+':1') if self.add_bos_token else ''} $B:1{(' '+eos+':1') if self.add_eos_token else ''}"

        special_tokens = []
        if self.add_bos_token:
            special_tokens.append((bos, bos_token_id))
        if self.add_eos_token:
            special_tokens.append((eos, eos_token_id))
        self._tokenizer.post_processor = processors.TemplateProcessing(
            single=single, pair=pair, special_tokens=special_tokens
        )

    @property
    def prefix_token(self):

        '''
        Returns the prefix token for the CodeLlamaTokenizerFast class.
        
        Args:
            self (CodeLlamaTokenizerFast): The instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            None: This method does not raise any exceptions.
        '''
        return self._prefix_token

    @property
    def prefix_id(self):

        """
        Returns the prefix token converted to its corresponding ID.
        
        Args:
            self (CodeLlamaTokenizerFast): An instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            None: If the prefix token is None.
        
        Raises:
            None.
        
        """
        if self._prefix_token is None:
            return None
        return self.convert_tokens_to_ids(self.prefix_token)

    @property
    def middle_token(self):

        """
        This method 'middle_token' is a property method in the class 'CodeLlamaTokenizerFast' that returns the middle token.
        
        Args:
            self: The instance of the class.
        
        Returns:
            None: This method returns the middle token or None if there is no middle token.
        
        Raises:
            This method does not raise any exceptions.
        """
        return self._middle_token

    @property
    def middle_id(self):

        """
        Returns the middle token ID of the CodeLlamaTokenizerFast instance.
        
        Args:
            self (CodeLlamaTokenizerFast): The instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            None: If the middle token is not set or is set to None.
            int: The ID of the middle token.
        
        Raises:
            None.
        
        This method retrieves the ID of the middle token in the CodeLlamaTokenizerFast instance. If the middle token is not set or is set to None, None is returned. Otherwise, the method calls the 'convert_tokens_to_ids' function to convert the middle token into its corresponding ID and returns the ID value.
        """
        if self._middle_token is None:
            return None
        return self.convert_tokens_to_ids(self.middle_token)

    @property
    def suffix_token(self):

        """
        This method, 'suffix_token', is a property method defined in the 'CodeLlamaTokenizerFast' class.
        
        Args:
            self: An instance of the 'CodeLlamaTokenizerFast' class. It is used to access the attributes and methods of the class within this method.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            This method does not raise any exceptions.
        
        """
        return self._suffix_token

    @property
    def suffix_id(self):

        """
        This method is defined in the `CodeLlamaTokenizerFast` class and is named `suffix_id`. It takes one parameter, `self`, which refers to the instance of the class.
        
        Args:
            - self: An instance of the `CodeLlamaTokenizerFast` class.
            
        Returns:
            - None: If the `_suffix_token` attribute is `None`, the method returns `None`.
            
        Raises:
            - None: This method does not raise any exceptions.
        
        Description:
        This method retrieves the suffix ID associated with the `_suffix_token` attribute. If the `_suffix_token` is `None`, indicating the absence of a suffix token, the method returns `None`. Otherwise, it calls the `convert_tokens_to_ids` method to convert the `_suffix_token` to its corresponding ID and returns the result.
        
        Note:
        - The `_suffix_token` attribute should be set before calling this method to ensure accurate results.
        - The return value is of type `None`.
        """
        if self._suffix_token is None:
            return None
        return self.convert_tokens_to_ids(self.suffix_token)

    @property
    def eot_id(self):

        """
        Returns the ID representation of the end-of-text (EOT) token in the CodeLlamaTokenizerFast class.
        
        Args:
            self: An instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            None: If the EOT token is not set.
            int: The ID representation of the EOT token.
        
        Raises:
            None.
        
        This method retrieves the ID representation of the EOT token. If the EOT token is not set (None), it returns None. Otherwise, it uses the 'convert_tokens_to_ids' method to convert the EOT token to its corresponding ID representation and returns it.
        """
        if self._eot_token is None:
            return None
        return self.convert_tokens_to_ids(self.eot_token)

    @property
    def eot_token(self):

        """
        eot_token method in the CodeLlamaTokenizerFast class.
        
        Args:
            self: The instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            None. The method returns the value of the _eot_token attribute.
        
        Raises:
            This method does not raise any exceptions.
        """
        return self._eot_token

    @property
    def add_eos_token(self):

        """
        Adds an end-of-sequence (EOS) token to the tokenizer.
        
        Args:
            self: The instance of the CodeLlamaTokenizerFast class.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            No exceptions are raised by this method.
        """
        return self._add_eos_token

    @property
    def add_bos_token(self):

        """
        Method to add a beginning of sentence (BOS) token to the tokenizer.
        
        Args:
            self: An instance of the CodeLlamaTokenizerFast class.
                It is used to access the tokenizer object.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            None
        """
        return self._add_bos_token

    @add_eos_token.setter
    def add_eos_token(self, value):

        """
        This method 'add_eos_token' is a setter method for the 'add_eos_token' property in the 'CodeLlamaTokenizerFast' class.
        
        Args:
            self (CodeLlamaTokenizerFast): The instance of the CodeLlamaTokenizerFast class.
            value (bool): A boolean value indicating whether to add an end-of-sequence token.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            This method does not explicitly raise any exceptions.
        """
        self._add_eos_token = value
        self.update_post_processor()

    @add_bos_token.setter
    def add_bos_token(self, value):

        """
        Sets the value of the 'add_bos_token' attribute in the CodeLlamaTokenizerFast class.
        
        Args:
            self (CodeLlamaTokenizerFast): An instance of the CodeLlamaTokenizerFast class.
            value: The value to be assigned to the 'add_bos_token' attribute. It can be of any type.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            None.
        
        This method updates the 'add_bos_token' attribute with the provided value and triggers the 'update_post_processor' method.
        """
        self._add_bos_token = value
        self.update_post_processor()

    def set_infilling_processor(self, reset, suffix_first=False, add_special_tokens=True):
        """
        Updates the normalizer to make sure the prompt format for `infilling` is respected. The infilling format is the
        following: if suffix_first
            " <PRE> <SUF>{suf} <MID> {pre}"
        else:
            " <PRE> {pre} <SUF>{suf} <MID>"

        If `reset` is set to `True`, the `normalizer` and `post_processor` are reset to their "normal" behaviour, which
        is to add a prefix space for the normalizer, and add a `bos_token` to the input text for the `post_processor`.
        """
        if reset:
            self._tokenizer.normalizer = normalizers.Sequence(
                [
                    normalizers.Prepend(prepend="▁"),
                    normalizers.Replace(pattern=" ", content="▁"),
                ]
            )
            self.update_post_processor()
            return

        self._tokenizer.normalizer = normalizers.Replace(pattern=" ", content="▁")
        pair = [self.bos_token] if self.add_bos_token and add_special_tokens else []
        special_tokens = [(self.bos_token, self.bos_token_id)] if self.add_bos_token and add_special_tokens else []
        if suffix_first:
            # format as " <PRE> <SUF>{suf} <MID> {pre}"
            pair += [self.prefix_token, self.suffix_token, "$B", self.middle_token, "$A"]
            special_tokens += [
                (self.prefix_token, self.prefix_id),
                (self.suffix_token, self.suffix_id),
                (self.middle_token, self.middle_id),
            ]
        else:
            # format as " <PRE> {pre} <SUF>{suf} <MID>"
            pair += [self.prefix_token, "$A", self.suffix_token, "$B", self.middle_token]
            special_tokens += [
                (self.prefix_token, self.prefix_id),
                (self.suffix_token, self.suffix_id),
                (self.middle_token, self.middle_id),
            ]

        if self.add_eos_token and add_special_tokens:
            pair += [self.eos_token]
            special_tokens += [(self.eos_token, self.eos_token_id)]
        self._tokenizer.post_processor = processors.TemplateProcessing(
            single="$A", pair=pair, special_tokens=special_tokens
        )

    def encode_plus(self, text, text_pair=None, suffix_first=False, add_special_tokens=True, **kwargs):

        """
        Encodes the given text and text pair into tokens using the CodeLlamaTokenizerFast class.
        
        Args:
            self (CodeLlamaTokenizerFast): An instance of the CodeLlamaTokenizerFast class.
            text (str): The input text to be encoded.
            text_pair (str, optional): The optional second input text to be encoded. Defaults to None.
            suffix_first (bool, optional): Specifies whether the suffix should be placed first. Defaults to False.
            add_special_tokens (bool, optional): Specifies whether to add special tokens. Defaults to True.
        
        Returns:
            tokens: The encoded tokens. This is an instance of a class defined in the CodeLlamaTokenizerFast class.
        
        Raises:
            ValueError: If the input includes a `prefix` and a `suffix` used for the infilling task, 
                        the `prefix_id, middle_id, suffix_id` must all be initialized.
                        Current values: (self.prefix_id, self.middle_id, self.suffix_id)
        """
        # hack to make sure the input is pre-process but outside rust
        text_pair = kwargs.pop("suffix", text_pair)
        if self.fill_token is not None and self.fill_token in text and text_pair is None:
            text, text_pair = text.split(self.fill_token)

        if text_pair is None or len(text_pair) < 1:
            return super().encode_plus(text, text_pair, add_special_tokens=add_special_tokens, **kwargs)

        if None in (self.prefix_id, self.middle_id, self.suffix_id):
            raise ValueError(
                "Then input includes a `prefix` and a `suffix` used for the infilling task,"
                " the `prefix_id, middle_id, suffix_id` must all be initialized. Current"
                f" values : {self.prefix_id, self.middle_id, self.suffix_id}"
            )

        self.set_infilling_processor(False, suffix_first=suffix_first, add_special_tokens=add_special_tokens)
        tokens = super().encode_plus(" " + text, text_pair=text_pair, add_special_tokens=True, **kwargs)
        self.set_infilling_processor(True)
        return tokens

    # Copied from transformers.models.llama.tokenization_llama_fast.LlamaTokenizerFast.save_vocabulary
    def save_vocabulary(self, save_directory: str, filename_prefix: Optional[str] = None) -> Tuple[str]:

        """
        Save the vocabulary for a fast tokenizer.
        
        Args:
            self (CodeLlamaTokenizerFast): An instance of the CodeLlamaTokenizerFast class.
            save_directory (str): The directory path where the vocabulary will be saved.
            filename_prefix (Optional[str], optional): A prefix to be added to the filename. Defaults to None.
        
        Returns:
            Tuple[str]: A tuple containing the path to the saved vocabulary file.
        
        Raises:
            ValueError: If the fast tokenizer does not have the necessary information to save the vocabulary for a slow tokenizer.
            FileNotFoundError: If the save_directory does not exist.
            IsADirectoryError: If the save_directory is not a directory.
        
        """
        if not self.can_save_slow_tokenizer:
            raise ValueError(
                "Your fast tokenizer does not have the necessary information to save the vocabulary for a slow "
                "tokenizer."
            )

        if not os.path.isdir(save_directory):
            logger.error(f"Vocabulary path ({save_directory}) should be a directory")
            return
        out_vocab_file = os.path.join(
            save_directory, (filename_prefix + "-" if filename_prefix else "") + VOCAB_FILES_NAMES["vocab_file"]
        )

        if os.path.abspath(self.vocab_file) != os.path.abspath(out_vocab_file):
            copyfile(self.vocab_file, out_vocab_file)

        return (out_vocab_file,)

    @property
    # Copied from transformers.models.llama.tokenization_llama.LlamaTokenizer.default_chat_template
    def default_chat_template(self):
        """
        LLaMA uses [INST] and [/INST] to indicate user messages, and <<SYS>> and <</SYS>> to indicate system messages.
        Assistant messages do not have special tokens, because LLaMA chat models are generally trained with strict
        user/assistant/user/assistant message ordering, and so assistant messages can be identified from the ordering
        rather than needing special tokens. The system message is partly 'embedded' in the first user message, which
        results in an unusual token ordering when it is present. This template should definitely be changed if you wish
        to fine-tune a model with more flexible role ordering!

        The output should look something like:

        <bos>[INST] B_SYS SystemPrompt E_SYS Prompt [/INST] Answer <eos><bos>[INST] Prompt [/INST] Answer <eos>
        <bos>[INST] Prompt [/INST]

        The reference for this chat template is [this code
        snippet](https://github.com/facebookresearch/llama/blob/556949fdfb72da27c2f4a40b7f0e4cf0b8153a28/llama/generation.py#L320-L362)
        in the original repository.
        """
        logger.warning_once(
            "\nNo chat template is defined for this tokenizer - using the default template "
            f"for the {self.__class__.__name__} class. If the default is not appropriate for "
            "your model, please set `tokenizer.chat_template` to an appropriate template. "
            "See https://hf-mirror.com/docs/transformers/main/chat_templating for more information.\n"
        )
        template = (
            "{% if messages[0]['role'] == 'system' %}"
            "{% set loop_messages = messages[1:] %}"  # Extract system message if it's present
            "{% set system_message = messages[0]['content'] %}"
            "{% elif USE_DEFAULT_PROMPT == true and not '<<SYS>>' in messages[0]['content'] %}"
            "{% set loop_messages = messages %}"  # Or use the default system message if the flag is set
            "{% set system_message = 'DEFAULT_SYSTEM_MESSAGE' %}"
            "{% else %}"
            "{% set loop_messages = messages %}"
            "{% set system_message = false %}"
            "{% endif %}"
            "{% for message in loop_messages %}"  # Loop over all non-system messages
            "{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}"
            "{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}"
            "{% endif %}"
            "{% if loop.index0 == 0 and system_message != false %}"  # Embed system message in first message
            "{% set content = '<<SYS>>\\n' + system_message + '\\n<</SYS>>\\n\\n' + message['content'] %}"
            "{% else %}"
            "{% set content = message['content'] %}"
            "{% endif %}"
            "{% if message['role'] == 'user' %}"  # After all of that, handle messages/roles in a fairly normal way
            "{{ bos_token + '[INST] ' + content.strip() + ' [/INST]' }}"
            "{% elif message['role'] == 'system' %}"
            "{{ '<<SYS>>\\n' + content.strip() + '\\n<</SYS>>\\n\\n' }}"
            "{% elif message['role'] == 'assistant' %}"
            "{{ ' '  + content.strip() + ' ' + eos_token }}"
            "{% endif %}"
            "{% endfor %}"
        )
        template = template.replace("USE_DEFAULT_PROMPT", "true" if self.use_default_system_prompt else "false")
        default_message = DEFAULT_SYSTEM_PROMPT.replace("\n", "\\n").replace("'", "\\'")
        template = template.replace("DEFAULT_SYSTEM_MESSAGE", default_message)

        return template

    def build_inputs_with_special_tokens(
        self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Build model inputs from a sequence or a pair of sequence for sequence classification tasks by concatenating and
        adding special tokens. The special tokens depend on calling set_lang.

        An NLLB sequence has the following format, where `X` represents the sequence:

        - `input_ids` (for encoder) `X [eos, src_lang_code]`
        - `decoder_input_ids`: (for decoder) `X [eos, tgt_lang_code]`

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
            return self.bos_token_id + token_ids_0 + self.eos_token_id
        return self.bos_token_id + token_ids_0 + token_ids_1 + self.eos_token_id

__all__ = ['CodeLlamaTokenizerFast']
