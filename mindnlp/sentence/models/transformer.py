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
"""Sentence transformer module"""

import json
import os
from typing import Dict, List, Optional, Tuple, Union

from mindspore import nn
from mindnlp.transformers import AutoModel, AutoTokenizer


class Transformer(nn.Cell):
    def __init__(
        self,
        model_name_or_path: str,
        max_seq_length: Optional[int] = None,
        model_args: Dict = {},
        cache_dir: Optional[str] = None,
        tokenizer_args: Dict = {},
        do_lower_case: bool = False,
        tokenizer_name_or_path: str = None,
    ):
        super(Transformer, self).__init__()
        self.config_keys = ["max_seq_length", "do_lower_case"]
        self.do_lower_case = do_lower_case

        # config = AutoConfig.from_pretrained(model_name_or_path, **model_args, cache_dir=cache_dir)
        self._load_model(model_name_or_path, cache_dir, **model_args)

        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name_or_path if tokenizer_name_or_path is not None else model_name_or_path,
            cache_dir=cache_dir,
            **tokenizer_args,
        )

        # No max_seq_length set. Try to infer from model
        if max_seq_length is None:
            if (
                hasattr(self.auto_model, "config")
                and hasattr(self.auto_model.config, "max_position_embeddings")
                and hasattr(self.tokenizer, "model_max_length")
            ):
                max_seq_length = min(self.auto_model.config.max_position_embeddings, self.tokenizer.model_max_length)

        self.max_seq_length = max_seq_length

        if tokenizer_name_or_path is not None:
            self.auto_model.config.tokenizer_class = self.tokenizer.__class__.__name__

    def _load_model(self, model_name_or_path, cache_dir, **model_args):
        """Loads the transformer model"""
        # config = AutoConfig.from_pretrained(model_name_or_path)
        config = None
        self.auto_model = AutoModel.from_pretrained(
            model_name_or_path, config=config, cache_dir=cache_dir, **model_args
        )

    def __repr__(self):
        return "Transformer({}) with Transformer model: {} ".format(
            self.get_config_dict(), self.auto_model.__class__.__name__
        )

    def construct(self, features):
        """Returns token_embeddings, cls_token"""
        trans_features = {"input_ids": features["input_ids"], "attention_mask": features["attention_mask"]}
        if "token_type_ids" in features:
            trans_features["token_type_ids"] = features["token_type_ids"]

        output_states = self.auto_model(**trans_features, return_dict=False)
        output_tokens = output_states[0]

        features.update({"token_embeddings": output_tokens, "attention_mask": features["attention_mask"]})

        if self.auto_model.config.output_hidden_states:
            all_layer_idx = 2
            if len(output_states) < 3:  # Some models only output last_hidden_states and all_hidden_states
                all_layer_idx = 1

            hidden_states = output_states[all_layer_idx]
            features.update({"all_layer_embeddings": hidden_states})

        return features

    def get_word_embedding_dimension(self) -> int:
        return self.auto_model.config.hidden_size

    def tokenize(self, texts: Union[List[str], List[Dict], List[Tuple[str, str]]], padding: Union[str, bool] = True):
        """
        Tokenizes a text and maps tokens to token-ids
        """
        output = {}
        if isinstance(texts[0], str):
            to_tokenize = [texts]
        elif isinstance(texts[0], dict):
            to_tokenize = []
            output["text_keys"] = []
            for lookup in texts:
                text_key, text = next(iter(lookup.items()))
                to_tokenize.append(text)
                output["text_keys"].append(text_key)
            to_tokenize = [to_tokenize]
        else:
            batch1, batch2 = [], []
            for text_tuple in texts:
                batch1.append(text_tuple[0])
                batch2.append(text_tuple[1])
            to_tokenize = [batch1, batch2]

        # strip
        to_tokenize = [[str(s).strip() for s in col] for col in to_tokenize]

        # Lowercase
        if self.do_lower_case:
            to_tokenize = [[s.lower() for s in col] for col in to_tokenize]

        output.update(
            self.tokenizer(
                *to_tokenize,
                padding=padding,
                truncation="longest_first",
                return_tensors="ms",
                max_length=self.max_seq_length,
            )
        )
        return output

    def get_config_dict(self):
        return {key: self.__dict__[key] for key in self.config_keys}

    def save(self, output_path: str, safe_serialization: bool = True):
        self.auto_model.save_pretrained(output_path, safe_serialization=safe_serialization)
        self.tokenizer.save_pretrained(output_path)

        with open(os.path.join(output_path, "sentence_bert_config.json"), "w") as fOut:
            json.dump(self.get_config_dict(), fOut, indent=2)

    @staticmethod
    def load(input_path: str):
        # Old classes used other config names than 'sentence_bert_config.json'
        for config_name in [
            "sentence_bert_config.json",
            "sentence_roberta_config.json",
            "sentence_distilbert_config.json",
            "sentence_camembert_config.json",
            "sentence_albert_config.json",
            "sentence_xlm-roberta_config.json",
            "sentence_xlnet_config.json",
        ]:
            sbert_config_path = os.path.join(input_path, config_name)
            if os.path.exists(sbert_config_path):
                break

        with open(sbert_config_path) as fIn:
            config = json.load(fIn)
        # Don't allow configs to set trust_remote_code
        if "model_args" in config:
            config["model_args"].pop("trust_remote_code")
        return Transformer(model_name_or_path=input_path, **config)
