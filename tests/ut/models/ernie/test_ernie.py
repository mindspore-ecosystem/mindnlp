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
"""Test Ernie"""
import gc
import unittest
import pytest
import numpy as np
import mindspore
from mindspore import Tensor
from mindnlp.models import (
    UIEConfig,
    UIE,
)


class TestModelingErnie(unittest.TestCase):
    r"""
    Test Ernie
    """

    def setUp(self):
        """
        Set up.
        """
        self.config = UIEConfig(
            vocab_size=1000,
            num_hidden_layers=2,
            hidden_size=128,
            num_hidden_layers2=2,
            num_attention_heads=2,
            intermediate_size=256,
        )

    def test_ernie_model(self):
        """
        Test ErnieModel
        """

    def test_uie_model(self):
        """
        Test UIEModel
        """

        model = UIE(self.config)
        input_ids = Tensor(np.random.randint(0, 100, (1, 20)), dtype=mindspore.int32)
        outputs = model(input_ids=input_ids)
        assert outputs[0].shape == (1, 20)
        assert outputs[1].shape == (1, 20)

    @pytest.mark.download
    def test_from_pretrained(self):
        """test from pretrained"""
        _ = UIE.from_pretrained("uie-base")

    def tearDown(self) -> None:
        gc.collect()
