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
MNLI dataset
"""
# pylint: disable=C0103

import os
from typing import Union, Tuple
from mindspore.dataset import GeneratorDataset
from mindnlp.utils.download import cache_file
from mindnlp.dataset.register import load
from mindnlp.configs import DEFAULT_ROOT
from mindnlp.utils import unzip

URL = "https://cims.nyu.edu/~sbowman/multinli/multinli_1.0.zip"

MD5 = "0f70aaf66293b3c088a864891db51353"


class Mnli:
    """
    MNLI dataset source
    """

    label_map = {
        "entailment": 0,
        "neutral": 1,
        "contradiction": 2,
    }

    def __init__(self, path) -> None:
        self.path: str = path
        self._label, self._sentence1, self._sentence2 = [], [], []
        self._load()

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            dataset = f.read()
        lines = dataset.split("\n")
        lines.pop(0)
        lines.pop(len(lines) - 1)
        for line in lines:
            l = line.split("\t")
            if l[0] in self.label_map:
                self._label.append(self.label_map[l[0]])
                self._sentence1.append(l[5])
                self._sentence2.append(l[6])

    def __getitem__(self, index):
        return self._label[index], self._sentence1[index], self._sentence2[index]

    def __len__(self):
        return len(self._label)


@load.register
def MNLI(
    root: str = DEFAULT_ROOT,
    split: Union[Tuple[str], str] = ("train", "dev_matched", "dev_mismatched"),
    proxies=None
):
    r"""
    Load the MNLI dataset
    Args:
        root (str): Directory where the datasets are saved.
            Default:~/.mindnlp
        split (str|Tuple[str]): Split or splits to be returned.
            Default:("train", "dev_matched", "dev_mismatched").
        proxies (dict): a dict to identify proxies,for example: {"https": "https://127.0.0.1:7890"}.

    Returns:
        - **datasets_list** (list) -A list of loaded datasets.
            If only one type of dataset is specified,such as 'trian',
            this dataset is returned instead of a list of datasets.

    Examples:
        >>> dataset_train, dataset_dev_matched, dataset_dev_mismatched = MNLI()
        >>> train_iter = dataset_train.create_tuple_iterator()
        >>> print(next(train_iter))

    """
    cache_dir = os.path.join(root, "datasets", "MNLI")
    path_dict = {
        "train": "multinli_1.0_train.txt",
        "dev_matched": "multinli_1.0_dev_matched.txt",
        "dev_mismatched": "multinli_1.0_dev_mismatched.txt",
    }
    column_names = ["label", "sentence1", "sentence2"]
    path_list = []
    datasets_list = []
    path, _ = cache_file(None, url=URL, cache_dir=cache_dir, md5sum=MD5, proxies=proxies)
    unzip(path, cache_dir)
    if isinstance(split, str):
        path_list.append(
            os.path.join(cache_dir, "multinli_1.0", path_dict[split])
        )
    else:
        for s in split:
            path_list.append(
                os.path.join(cache_dir, "multinli_1.0", path_dict[s])
            )
    for path in path_list:
        datasets_list.append(
            GeneratorDataset(
                source=Mnli(path), column_names=column_names, shuffle=False
            )
        )
    if len(path_list) == 1:
        return datasets_list[0]
    return datasets_list
