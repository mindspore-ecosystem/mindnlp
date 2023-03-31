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
"""Test Erine"""

import unittest
import numpy as np
import mindspore
from mindspore import Tensor
from mindnlp.models.erine import erine_config, erine


class TestModelingErine(unittest.TestCase):
    r"""
    Test GPT
    """
    def setUp(self):
        """
        Set up.
        """
        self.input = None

    def test_erine_embedding(self):
        r"""
        Test Erine Embedding
        """
        config = erine_config.ErnieConfig()
        config.vocab_size=100
        config.hidden_size=128
        model = erine.ErnieEmbeddings(config,weight_attr='normal')
        hidden_states = Tensor(np.random.randn(2, 512), mindspore.int32)
        mlp_output = model(hidden_states)
        assert mlp_output.shape == (2, 512, 128)
        