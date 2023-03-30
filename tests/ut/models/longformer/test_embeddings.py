# Copyright 2022 Huawei Technologies Co., Ltd
# Copyright 2022 Huawei Technologies Co., Ltd
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
"""Test Longformer"""
import unittest
import numpy as np
import mindspore
from mindspore import Tensor
from mindnlp.models.longformer.longformer import LongformerEmbeddings
from mindnlp.models.longformer.longformer_config import LongformerConfig
from mindnlp.models.longformer.longformer import LongformerSelfAttention
from mindnlp.models.longformer.longformer import LongformerSelfOutput
from mindnlp.models.longformer.longformer import LongformerAttention
from mindnlp.models.longformer.longformer import LongformerIntermediate
from mindnlp.models.longformer.longformer import LongformerOutput

class TestModelingEmbeddings(unittest.TestCase):
    r"""
    Test model bert
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_modeling_longformer_embedding(self):
        r"""
        Test model bert with pynative mode
        """
        ms_config = LongformerConfig()
        ms_model = LongformerEmbeddings(ms_config)
        ms_model.set_train(False)
        tensor = np.random.randint(1, 10, (2, 2))
        ms_input_ids = Tensor.from_numpy(tensor)
        ms_outputs = ms_model(ms_input_ids)
        assert (2, 2, 768) == ms_outputs.shape


class TestModelingSelfAttention(unittest.TestCase):
    r"""
    Test model bert
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_modeling_longformer_embedding(self):
        r"""
        Test model bert with pynative mode
        """
        ms_config = LongformerConfig(attention_window=[8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8])
        ms_model = LongformerSelfAttention(ms_config, 1)
        ms_model.set_train(False)
        tensor = np.random.randint(1, 10, (1, 64, 768))
        tensor_attention_mask = np.random.randint(0, 10, (1, 64))
        tensor_is_index_global = np.random.randint(0, 2, (1, 64))
        tensor_is_index_masked = np.random.randint(0, 2, (1, 64))
        ms_input_ids = mindspore.Tensor(tensor, dtype=mindspore.float32)
        ms_outputs = ms_model(ms_input_ids,
                              attention_mask=mindspore.Tensor(tensor_attention_mask, dtype=mindspore.float32),
                              is_index_masked=mindspore.Tensor(tensor_is_index_masked, dtype=mindspore.bool_),
                              is_index_global_attn=mindspore.Tensor(tensor_is_index_global, dtype=mindspore.bool_),
                              is_global_attn=True,
                              output_attentions=False)
        assert (1, 64, 768) == ms_outputs[0].shape


class TestModelingSelfOutput(unittest.TestCase):
    r"""
    Test model bert
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_modeling_longformer_embedding(self):
        r"""
        Test model bert with pynative mode
        """
        ms_config = LongformerConfig()
        ms_model = LongformerSelfOutput(ms_config)
        ms_model.set_train(False)
        hidden_states = np.random.randint(1, 10, (1, 8, 768))
        input_tensor = np.random.randint(1, 10, (1, 8, 768))
        ms_hidden_states = Tensor(hidden_states, dtype=mindspore.float32)
        ms_input_tensors = Tensor(input_tensor, dtype=mindspore.float32)

        ms_outputs = ms_model(ms_hidden_states, ms_input_tensors)
        assert (1, 8, 768) == ms_outputs.shape


class TestModelingAttention(unittest.TestCase):
    r"""
    Test model bert
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_modeling_longformer_embedding(self):
        r"""
        Test model bert with pynative mode
        """
        ms_config = LongformerConfig(attention_window=[8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8])
        ms_model = LongformerAttention(ms_config)
        ms_model.set_train(False)
        hidden_states = np.random.randint(1, 10, (1, 8, 768))
        attention_mask = np.random.randint(1, 10, (1, 8))
        is_index_mask = np.random.randint(0, 2, (1, 8))
        is_index_global_attn = np.random.randint(0, 2, (1, 8))
        is_global_attn = True
        output_attentions = False
        ms_hidden_states = mindspore.Tensor(hidden_states, dtype=mindspore.float32)
        ms_attention_mask = mindspore.Tensor(attention_mask, dtype=mindspore.float32)
        ms_is_index_mask = mindspore.Tensor(is_index_mask, dtype=mindspore.bool_)
        ms_is_index_global_attn = mindspore.Tensor(is_index_global_attn, dtype=mindspore.bool_)
        ms_outputs = ms_model(
            hidden_states=ms_hidden_states,
            attention_mask=ms_attention_mask,
            is_index_masked=ms_is_index_mask,
            is_index_global_attn=ms_is_index_global_attn,
            is_global_attn=is_global_attn,
            output_attentions=output_attentions
        )
        assert (1, 8, 768) == ms_outputs[0].shape


class TestModelingIntermediate(unittest.TestCase):
    r"""
    Test model bert
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_modeling_longformer_embedding(self):
        r"""
        Test model bert with pynative mode
        """
        ms_config = LongformerConfig(intermediate_size=10)
        ms_model = LongformerIntermediate(ms_config)
        hidden_states = np.random.randint(1, 10, (1, 8, 768))
        ms_hidden_states = mindspore.Tensor(hidden_states, dtype=mindspore.float32)
        ms_outputs = ms_model(
            hidden_states=ms_hidden_states
        )
        assert (1, 8, 10) == ms_outputs.shape


class TestModelingOutput(unittest.TestCase):
    r"""
    Test model bert
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_modeling_longformer_embedding(self):
        r"""
        Test model bert with pynative mode
        """
        ms_config = LongformerConfig(intermediate_size=768)
        ms_model = LongformerOutput(ms_config)
        ms_model.set_train(False)
        hidden_states = np.random.randint(1, 10, (1, 8, 768))
        input_tensor = np.random.randint(1, 10, (1, 8, 768))
        ms_hidden_states = Tensor(hidden_states, dtype=mindspore.float32)
        ms_input_tensors = Tensor(input_tensor, dtype=mindspore.float32)

        ms_outputs = ms_model(ms_hidden_states, ms_input_tensors)
        assert (8, 768) == ms_outputs[0].shape