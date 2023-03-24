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
"""
Test MRPC
"""
import os
import shutil
import unittest
import pytest
import mindspore as ms
from mindnlp.dataset import MRPC, MRPC_Process
from mindnlp import load_dataset, process

from mindnlp.transforms import BasicTokenizer


class TestMRPC(unittest.TestCase):
    r"""
    Test MRPC
    """

    @classmethod
    def setUpClass(cls):
        cls.root = os.path.join(os.path.expanduser("~"), ".mindnlp")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    @pytest.mark.dataset
    def test_mrpc(self):
        """Test mrpc"""
        num_lines = {
            "train": 4076,
            "test": 1725,
        }
        dataset_train, dataset_test = MRPC(
            root=self.root, split=("train", "test"))
        assert dataset_train.get_dataset_size() == num_lines["train"]
        assert dataset_test.get_dataset_size() == num_lines["test"]

        dataset_train = MRPC(root=self.root, split="train")
        dataset_test = MRPC(root=self.root, split="test")
        assert dataset_train.get_dataset_size() == num_lines["train"]
        assert dataset_test.get_dataset_size() == num_lines["test"]

    @pytest.mark.dataset
    def test_mrpc_by_register(self):
        """test mrpc by register"""
        _ = load_dataset('MRPC', root=self.root, split=('train', 'test'),)

    @pytest.mark.dataset
    def test_mrpc_process(self):
        r"""
        Test MRPC_Process
        """

        train_dataset, _ = MRPC()
        train_dataset, vocab = MRPC_Process(train_dataset)

        train_dataset = train_dataset.create_tuple_iterator()
        assert (next(train_dataset)[1]).dtype == ms.int32
        assert (next(train_dataset)[2]).dtype == ms.int32

        for _, value in vocab.vocab().items():
            assert isinstance(value, int)
            break

    @pytest.mark.dataset
    def test_mrpc_process_by_register(self):
        """test mrpc process by register"""
        train_dataset, _ = MRPC()
        train_dataset, vocab = process('MRPC',
                                dataset=train_dataset,
                                column=("sentence1", "sentence2"),
                                tokenizer=BasicTokenizer(),
                                vocab=None
                                )

        train_dataset = train_dataset.create_tuple_iterator()
        assert (next(train_dataset)[1]).dtype == ms.int32
        assert (next(train_dataset)[2]).dtype == ms.int32

        for _, value in vocab.vocab().items():
            assert isinstance(value, int)
            break
