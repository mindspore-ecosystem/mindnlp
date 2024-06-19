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
"""Testing suite for the PyTorch Dinov2 model."""

import unittest

from mindnlp.transformers import Dinov2Config
from mindnlp.utils.testing_utils import is_flaky, require_mindspore, slow
from mindnlp.utils import cached_property, is_mindspore_available

from ...test_backbone_common import BackboneTesterMixin
from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, floats_tensor, ids_tensor
# from ...test_pipeline_mixin import PipelineTesterMixin

import numpy as np

if is_mindspore_available():
    import mindspore
    from mindspore import nn

    from mindnlp.transformers import Dinov2ForImageClassification, Dinov2Model, Dinov2Backbone

    from PIL import Image

    from mindnlp.transformers import AutoImageProcessor


class Dinov2ModelTester:
    def __init__(
        self,
        parent,
        batch_size=13,
        image_size=30,
        patch_size=2,
        num_channels=3,
        is_training=True,
        use_labels=True,
        hidden_size=32,
        num_hidden_layers=2,
        num_attention_heads=4,
        intermediate_size=37,
        hidden_act="gelu",
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        type_sequence_label_size=10,
        initializer_range=0.02,
        scope=None,
    ):
        self.parent = parent
        self.batch_size = batch_size
        self.image_size = image_size
        self.patch_size = patch_size
        self.num_channels = num_channels
        self.is_training = is_training
        self.use_labels = use_labels
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size
        self.hidden_act = hidden_act
        self.hidden_dropout_prob = hidden_dropout_prob
        self.attention_probs_dropout_prob = attention_probs_dropout_prob
        self.type_sequence_label_size = type_sequence_label_size
        self.initializer_range = initializer_range
        self.scope = scope

        # in Dinov2, the seq length equals the number of patches + 1 (we add 1 for the [CLS] token)
        num_patches = (image_size // patch_size) ** 2
        self.seq_length = num_patches + 1

    def prepare_config_and_inputs(self):
        pixel_values = floats_tensor([self.batch_size, self.num_channels, self.image_size, self.image_size])

        labels = None
        if self.use_labels:
            labels = ids_tensor([self.batch_size], self.type_sequence_label_size)

        config = self.get_config()

        return config, pixel_values, labels

    def get_config(self):
        return Dinov2Config(
            image_size=self.image_size,
            patch_size=self.patch_size,
            num_channels=self.num_channels,
            hidden_size=self.hidden_size,
            num_hidden_layers=self.num_hidden_layers,
            num_attention_heads=self.num_attention_heads,
            intermediate_size=self.intermediate_size,
            hidden_act=self.hidden_act,
            hidden_dropout_prob=self.hidden_dropout_prob,
            attention_probs_dropout_prob=self.attention_probs_dropout_prob,
            is_decoder=False,
            initializer_range=self.initializer_range,
        )

    def create_and_check_model(self, config, pixel_values, labels):
        model = Dinov2Model(config=config)
        model.set_train(False)
        result = model(pixel_values)
        self.parent.assertEqual(result.last_hidden_state.shape, (self.batch_size, self.seq_length, self.hidden_size))

    def create_and_check_backbone(self, config, pixel_values, labels):
        model = Dinov2Backbone(config=config)
        model.set_train(False)
        result = model(pixel_values)

        # verify hidden states
        self.parent.assertEqual(len(result.feature_maps), len(config.out_features))
        expected_size = self.image_size // config.patch_size
        self.parent.assertListEqual(
            list(result.feature_maps[0].shape), [self.batch_size, model.channels[0], expected_size, expected_size]
        )

        # verify channels
        self.parent.assertEqual(len(model.channels), len(config.out_features))

        # verify backbone works with out_features=None
        config.out_features = None
        model = Dinov2Backbone(config=config)
        model.set_train(False)
        result = model(pixel_values)

        # verify feature maps
        self.parent.assertEqual(len(result.feature_maps), 1)
        self.parent.assertListEqual(
            list(result.feature_maps[0].shape), [self.batch_size, model.channels[0], expected_size, expected_size]
        )

        # verify channels
        self.parent.assertEqual(len(model.channels), 1)

        # verify backbone works with apply_layernorm=False and reshape_hidden_states=False
        config.apply_layernorm = False
        config.reshape_hidden_states = False

        model = Dinov2Backbone(config=config)
        model.set_train(False)
        result = model(pixel_values)

        # verify feature maps
        self.parent.assertEqual(len(result.feature_maps), 1)
        self.parent.assertListEqual(
            list(result.feature_maps[0].shape), [self.batch_size, self.seq_length, self.hidden_size]
        )

    def create_and_check_for_image_classification(self, config, pixel_values, labels):
        config.num_labels = self.type_sequence_label_size
        model = Dinov2ForImageClassification(config)
        model.set_train(False)
        result = model(pixel_values, labels=labels)
        self.parent.assertEqual(result.logits.shape, (self.batch_size, self.type_sequence_label_size))

        # test greyscale images
        config.num_channels = 1
        model = Dinov2ForImageClassification(config)
        model.set_train(False)

        pixel_values = floats_tensor([self.batch_size, 1, self.image_size, self.image_size])
        result = model(pixel_values)
        self.parent.assertEqual(result.logits.shape, (self.batch_size, self.type_sequence_label_size))

    def prepare_config_and_inputs_for_common(self):
        config_and_inputs = self.prepare_config_and_inputs()
        (
            config,
            pixel_values,
            labels,
        ) = config_and_inputs
        inputs_dict = {"pixel_values": pixel_values}
        return config, inputs_dict


@require_mindspore
class Dinov2ModelTest(ModelTesterMixin,  unittest.TestCase):
    """
    Here we also overwrite some of the tests of test_modeling_common.py, as Dinov2 does not use input_ids, inputs_embeds,
    attention_mask and seq_length.
    """

    all_model_classes = (
        (
            Dinov2ForImageClassification,
            Dinov2Backbone,
        )
        if is_mindspore_available()
        else ()
    )
    pipeline_model_mapping = (
        {"image-feature-extraction": Dinov2Model, "image-classification": Dinov2ForImageClassification}
        if is_mindspore_available()
        else {}
    )
    fx_compatible = True

    test_pruning = False
    test_resize_embeddings = False
    test_head_masking = False

    def setUp(self):
        self.model_tester = Dinov2ModelTester(self)
        self.config_tester = ConfigTester(self, config_class=Dinov2Config, has_text_modality=False, hidden_size=37)

    @is_flaky(max_attempts=3, description="measure of timing is somehow flaky.")
    def test_initialization(self):
        super().test_initialization()

    def test_config(self):
        self.config_tester.run_common_tests()

    @unittest.skip(reason="Dinov2 does not use inputs_embeds")
    def test_inputs_embeds(self):
        pass

    @unittest.skip(
        reason="This architecure seem to not compute gradients properly when using GC, check: https://github.com/huggingface/transformers/pull/27124"
    )
    def test_training_gradient_checkpointing(self):
        pass

    @unittest.skip(
        reason="This architecure seem to not compute gradients properly when using GC, check: https://github.com/huggingface/transformers/pull/27124"
    )
    def test_training_gradient_checkpointing_use_reentrant(self):
        pass

    @unittest.skip(
        reason="This architecure seem to not compute gradients properly when using GC, check: https://github.com/huggingface/transformers/pull/27124"
    )
    def test_training_gradient_checkpointing_use_reentrant_false(self):
        pass
    
    # override since we have embeddings / LM heads over multiple codebooks
    def test_model_common_attributes(self):
        config, _ = self.model_tester.prepare_config_and_inputs_for_common()
        for model_class in self.all_model_classes:
            model = model_class(config)
            self.assertIsInstance(model.get_input_embeddings(), (nn.Cell))
            x = model.get_output_embeddings()
            self.assertTrue(x is None or isinstance(x, nn.Dense))
    
    # def test_model_get_set_embeddings(self):
    #     config, _ = self.model_tester.prepare_config_and_inputs_for_common()
    #     for model_class in self.all_model_classes:
    #         model = model_class(config)
    #         self.assertIsInstance(model.get_input_embeddings(), (nn.Cell))
    #         x = model.get_output_embeddings()
    #         self.assertTrue(x is None or isinstance(x, nn.Dense))

    def test_model(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_model(*config_and_inputs)

    def test_backbone(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_backbone(*config_and_inputs)

    def test_for_image_classification(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_for_image_classification(*config_and_inputs)

    @unittest.skip(reason="Dinov2 does not support feedforward chunking yet")
    def test_feed_forward_chunking(self):
        pass

    @slow
    def test_model_from_pretrained(self):
        model_name = "facebook/dinov2-base"
        model = Dinov2Model.from_pretrained(model_name, from_pt=True)
        self.assertIsNotNone(model)


# We will verify our results on an image of cute cats
def prepare_img():
    image = Image.open("./tests/fixtures/tests_samples/COCO/000000039769.png")
    return image


@require_mindspore
class Dinov2ModelIntegrationTest(unittest.TestCase):
    @cached_property
    def default_image_processor(self):
        return AutoImageProcessor.from_pretrained("facebook/dinov2-base") if is_mindspore_available() else None

    @slow
    def test_inference_no_head(self):
        model = Dinov2Model.from_pretrained("facebook/dinov2-base")

        image_processor = self.default_image_processor
        image = prepare_img()
        inputs = image_processor(image, return_tensors="ms")


        # forward pass
        with mindspore._no_grad():
            outputs = model(**inputs)

        # verify the last hidden states
        expected_shape = (1, 257, 768)
        self.assertEqual(outputs.last_hidden_state.shape, expected_shape)

        expected_slice = mindspore.tensor(
            [[-2.1747, -0.4729, 1.0936], [-3.2780, -0.8269, -0.9210], [-2.9129, 1.1284, -0.7306]],
        )
        self.assertTrue(np.allclose(outputs.last_hidden_state[0, :3, :3].asnumpy(), expected_slice.asnumpy(), atol=1e-4))


@require_mindspore
class Dinov2BackboneTest(unittest.TestCase, BackboneTesterMixin):
    all_model_classes = (Dinov2Backbone,) if is_mindspore_available() else ()
    config_class = Dinov2Config

    has_attentions = False

    def setUp(self):
        self.model_tester = Dinov2ModelTester(self)
