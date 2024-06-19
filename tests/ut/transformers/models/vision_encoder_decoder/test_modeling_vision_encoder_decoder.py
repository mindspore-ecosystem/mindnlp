<<<<<<< HEAD
# Copyright 2024 Huawei Technologies Co., Ltd
=======
# coding=utf-8
# Copyright 2021 HuggingFace Inc. team.
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
<<<<<<< HEAD
# http://www.apache.org/licenses/LICENSE-2.0
=======
#     http://www.apache.org/licenses/LICENSE-2.0
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
<<<<<<< HEAD
# ============================================

import re
import tempfile
import unittest

from datasets import load_dataset
from huggingface_hub import hf_hub_download
from packaging import version

from mindnlp.transformers import DonutProcessor, NougatProcessor, TrOCRProcessor
from mindnlp.utils.testing_utils import (
    require_sentencepiece,
=======

import tempfile
import unittest

from mindnlp.utils.testing_utils import (
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
    require_mindspore,
    require_vision,
    slow,
    to_2tuple,
<<<<<<< HEAD
    is_vision_available,
    is_mindspore_available,
)

from mindnlp.utils import cached_property
from ...test_modeling_common import floats_tensor, ids_tensor, random_attention_mask
from ..bart.test_modeling_bart import BartModelTester
from ..bert.test_modeling_bert import BertModelTester
from ..deit.test_modeling_deit import DeiTModelTester
from ..layoutlmv3.test_modeling_layoutlmv3 import LayoutLMv3ModelTester
from ..swin.test_modeling_swin import SwinModelTester
from ..trocr.test_modeling_trocr import TrOCRStandaloneDecoderModelTester
from ..vit.test_modeling_vit import ViTModelTester


if is_mindspore_available():
    import numpy as np
    import mindspore as ms
=======
    is_mindspore_available,
    is_vision_available,
)

from ...test_modeling_common import floats_tensor, ids_tensor, random_attention_mask
from ..bart.test_modeling_bart import BartModelTester
from ..bert.test_modeling_bert import BertModelTester
from ..swin.test_modeling_swin import SwinModelTester
from ..vit.test_modeling_vit import ViTModelTester

if is_mindspore_available():
    import numpy as np
    import mindspore
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d

    from mindnlp.transformers import (
        GPT2Tokenizer,
        BartForCausalLM,
        BertLMHeadModel,
<<<<<<< HEAD
        DeiTModel,
        LayoutLMv3Model,
        SwinModel,
        TrOCRForCausalLM,
=======
        SwinModel,
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        VisionEncoderDecoderConfig,
        VisionEncoderDecoderModel,
        ViTModel,
    )
    from mindnlp.transformers.modeling_outputs import BaseModelOutput


if is_vision_available():
<<<<<<< HEAD
    import PIL
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
    from PIL import Image

    from mindnlp.transformers import ViTImageProcessor


@require_mindspore
class EncoderDecoderMixin:
    def get_encoder_decoder_model(self, config, decoder_config):
        pass

    def prepare_config_and_inputs(self):
        pass

    def get_pretrained_model_and_inputs(self):
        pass

    def check_encoder_decoder_model_from_pretrained_configs(
        self, config, decoder_config, decoder_input_ids, decoder_attention_mask, pixel_values=None, **kwargs
    ):
        encoder_decoder_config = VisionEncoderDecoderConfig.from_encoder_decoder_configs(config, decoder_config)
        self.assertTrue(encoder_decoder_config.decoder.is_decoder)

        enc_dec_model = VisionEncoderDecoderModel(encoder_decoder_config)
        enc_dec_model.set_train(False)

        self.assertTrue(enc_dec_model.config.is_encoder_decoder)

        outputs_encoder_decoder = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
        )

        self.assertEqual(
            outputs_encoder_decoder["logits"].shape, (decoder_input_ids.shape + (decoder_config.vocab_size,))
        )

    def check_encoder_decoder_model(
        self, config, decoder_config, decoder_input_ids, decoder_attention_mask, pixel_values=None, **kwargs
    ):
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        self.assertTrue(enc_dec_model.config.decoder.is_decoder)
        self.assertTrue(enc_dec_model.config.decoder.add_cross_attention)
        self.assertTrue(enc_dec_model.config.is_encoder_decoder)
        outputs_encoder_decoder = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            output_hidden_states=True,
        )
        self.assertEqual(
            outputs_encoder_decoder["logits"].shape, (decoder_input_ids.shape + (decoder_config.vocab_size,))
        )
        encoder_outputs = BaseModelOutput(last_hidden_state=outputs_encoder_decoder.encoder_hidden_states[-1])
        outputs_encoder_decoder = enc_dec_model(
            encoder_outputs=encoder_outputs,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
        )

        self.assertEqual(
            outputs_encoder_decoder["logits"].shape, (decoder_input_ids.shape + (decoder_config.vocab_size,))
        )

    def check_encoder_decoder_model_from_pretrained(
        self,
        config,
        decoder_config,
        decoder_input_ids,
        decoder_attention_mask,
        return_dict,
        pixel_values=None,
        **kwargs,
    ):
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        kwargs = {"encoder_model": encoder_model, "decoder_model": decoder_model, "return_dict": return_dict}
        enc_dec_model = VisionEncoderDecoderModel.from_encoder_decoder_pretrained(**kwargs)
        outputs_encoder_decoder = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            output_hidden_states=True,
            return_dict=True,
        )

        self.assertEqual(
            outputs_encoder_decoder["logits"].shape, (decoder_input_ids.shape + (decoder_config.vocab_size,))
        )

    def check_save_and_load(
        self, config, decoder_config, decoder_input_ids, decoder_attention_mask, pixel_values=None, **kwargs
    ):
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        enc_dec_model.set_train(False)
        outputs = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
        )
<<<<<<< HEAD
        out_2 = outputs[0].asnumpy()
=======
        out_2 = outputs[0].numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        out_2[np.isnan(out_2)] = 0

        with tempfile.TemporaryDirectory() as tmpdirname:
            enc_dec_model.save_pretrained(tmpdirname)
            enc_dec_model = VisionEncoderDecoderModel.from_pretrained(tmpdirname)

            after_outputs = enc_dec_model(
                pixel_values=pixel_values,
                decoder_input_ids=decoder_input_ids,
                decoder_attention_mask=decoder_attention_mask,
            )
<<<<<<< HEAD
            out_1 = after_outputs[0].asnumpy()
=======
            out_1 = after_outputs[0].numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
            out_1[np.isnan(out_1)] = 0
            max_diff = np.amax(np.abs(out_1 - out_2))
            self.assertLessEqual(max_diff, 1e-5)

    def check_save_and_load_encoder_decoder_model(
        self, config, decoder_config, decoder_input_ids, decoder_attention_mask, pixel_values=None, **kwargs
    ):
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        enc_dec_model.set_train(False)
        outputs = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
        )
<<<<<<< HEAD
        out_2 = outputs[0].asnumpy()
=======
        out_2 = outputs[0].numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        out_2[np.isnan(out_2)] = 0

        with tempfile.TemporaryDirectory() as encoder_tmp_dirname, tempfile.TemporaryDirectory() as decoder_tmp_dirname:
            enc_dec_model.encoder.save_pretrained(encoder_tmp_dirname)
            enc_dec_model.decoder.save_pretrained(decoder_tmp_dirname)
            VisionEncoderDecoderModel.from_encoder_decoder_pretrained(
                encoder_pretrained_model_name_or_path=encoder_tmp_dirname,
                decoder_pretrained_model_name_or_path=decoder_tmp_dirname,
            )

            after_outputs = enc_dec_model(
                pixel_values=pixel_values,
                decoder_input_ids=decoder_input_ids,
                decoder_attention_mask=decoder_attention_mask,
            )
<<<<<<< HEAD
            out_1 = after_outputs[0].asnumpy()
=======
            out_1 = after_outputs[0].numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
            out_1[np.isnan(out_1)] = 0
            max_diff = np.amax(np.abs(out_1 - out_2))
            self.assertLessEqual(max_diff, 1e-5)

    def check_encoder_decoder_model_output_attentions(
        self,
        config,
        decoder_config,
        decoder_input_ids,
        decoder_attention_mask,
        labels=None,
        pixel_values=None,
        **kwargs,
    ):
<<<<<<< HEAD
        # make the decoder inputs a different shape from the encoder inputs to harden the test
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        decoder_input_ids = decoder_input_ids[:, :-1]
        decoder_attention_mask = decoder_attention_mask[:, :-1]
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        outputs_encoder_decoder = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            output_attentions=True,
        )

        encoder_attentions = outputs_encoder_decoder["encoder_attentions"]
        self.assertEqual(len(encoder_attentions), config.num_hidden_layers)

<<<<<<< HEAD
        # in ViT, the seq_len equals the number of patches + 1 (we add 1 for the [CLS] token)
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        image_size = to_2tuple(encoder_model.config.image_size)
        patch_size = to_2tuple(encoder_model.config.patch_size)
        num_patches = (image_size[1] // patch_size[1]) * (image_size[0] // patch_size[0])
        seq_len = num_patches + 1
        self.assertEqual(encoder_attentions[0].shape[-3:], (config.num_attention_heads, seq_len, seq_len))

        decoder_attentions = outputs_encoder_decoder["decoder_attentions"]
        num_decoder_layers = (
            decoder_config.num_decoder_layers
            if hasattr(decoder_config, "num_decoder_layers")
            else decoder_config.num_hidden_layers
        )
        self.assertEqual(len(decoder_attentions), num_decoder_layers)

        self.assertEqual(
            decoder_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, decoder_input_ids.shape[-1], decoder_input_ids.shape[-1]),
        )

        cross_attentions = outputs_encoder_decoder["cross_attentions"]
        self.assertEqual(len(cross_attentions), num_decoder_layers)

        cross_attention_input_seq_len = decoder_input_ids.shape[-1]
        self.assertEqual(
            cross_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, cross_attention_input_seq_len, seq_len),
        )

    def check_encoder_decoder_model_generate(self, config, decoder_config, pixel_values=None, **kwargs):
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)

<<<<<<< HEAD
        # Generate until max length
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        if hasattr(enc_dec_model.config, "eos_token_id"):
            enc_dec_model.config.eos_token_id = None
        if hasattr(enc_dec_model.config, "decoder") and hasattr(enc_dec_model.config.decoder, "eos_token_id"):
            enc_dec_model.config.decoder.eos_token_id = None
        if hasattr(enc_dec_model.generation_config, "eos_token_id"):
            enc_dec_model.generation_config.eos_token_id = None

        inputs = pixel_values

<<<<<<< HEAD
        # Bert does not have a bos token id, so use pad_token_id instead
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        generated_output = enc_dec_model.generate(
            inputs, decoder_start_token_id=enc_dec_model.config.decoder.pad_token_id
        )
        self.assertEqual(generated_output.shape, (inputs.shape[0],) + (decoder_config.max_length,))

    def test_encoder_decoder_model(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_encoder_decoder_model(**input_ids_dict)

    def test_encoder_decoder_model_from_pretrained_configs(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_encoder_decoder_model_from_pretrained_configs(**input_ids_dict)

    def test_encoder_decoder_model_from_pretrained(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_encoder_decoder_model_from_pretrained(**input_ids_dict, return_dict=False)

    def test_encoder_decoder_model_from_pretrained_return_dict(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_encoder_decoder_model_from_pretrained(**input_ids_dict, return_dict=True)

    def test_save_and_load_from_pretrained(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_save_and_load(**input_ids_dict)

    def test_save_and_load_from_encoder_decoder_pretrained(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_save_and_load_encoder_decoder_model(**input_ids_dict)

    def test_encoder_decoder_model_output_attentions(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_encoder_decoder_model_output_attentions(**input_ids_dict)

    def test_encoder_decoder_model_generate(self):
        input_ids_dict = self.prepare_config_and_inputs()
        self.check_encoder_decoder_model_generate(**input_ids_dict)

<<<<<<< HEAD
=======
    def test_training_gradient_checkpointing(self):
        inputs_dict = self.prepare_config_and_inputs()
        encoder_model, decoder_model = self.get_encoder_decoder_model(
            inputs_dict["config"], inputs_dict["decoder_config"]
        )

        model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        model.set_train(True)
        model.config.decoder_start_token_id = 0
        model.config.pad_token_id = 0

        model_inputs = {
            "pixel_values": inputs_dict["pixel_values"],
            "labels": inputs_dict["labels"],
            "decoder_input_ids": inputs_dict["decoder_input_ids"],
        }

        loss = model(**model_inputs).loss
        # mindspore.grad(model)(**model_inputs)

>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
    @slow
    def test_real_model_save_load_from_pretrained(self):
        model_2, inputs = self.get_pretrained_model_and_inputs()

        outputs = model_2(**inputs)
<<<<<<< HEAD
        out_2 = outputs[0].asnumpy()
=======
        out_2 = outputs[0].numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        out_2[np.isnan(out_2)] = 0

        with tempfile.TemporaryDirectory() as tmp_dirname:
            model_2.save_pretrained(tmp_dirname)
            model_1 = VisionEncoderDecoderModel.from_pretrained(tmp_dirname)

            after_outputs = model_1(**inputs)
<<<<<<< HEAD
            out_1 = after_outputs[0].asnumpy()
=======
            out_1 = after_outputs[0].numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
            out_1[np.isnan(out_1)] = 0
            max_diff = np.amax(np.abs(out_1 - out_2))
            self.assertLessEqual(max_diff, 1e-5)


@require_mindspore
<<<<<<< HEAD
class DeiT2RobertaModelTest(EncoderDecoderMixin, unittest.TestCase):
    def get_pretrained_model_and_inputs(self):
        model = VisionEncoderDecoderModel.from_encoder_decoder_pretrained(
            encoder_pretrained_model_name_or_path="hf-internal-testing/tiny-random-deit",
            decoder_pretrained_model_name_or_path="hf-internal-testing/tiny-random-roberta"
        )
        batch_size = 13
        pixel_values = floats_tensor(
            [
                batch_size,
                model.encoder.config.num_channels,
                model.encoder.config.image_size,
                model.encoder.config.image_size,
            ]
        )
        # for DEiT, the sequence length is equal to the number of patches + 2 (for the [CLS] and distillation tokens)
        decoder_input_ids = ids_tensor([batch_size, 4], model.decoder.config.vocab_size)
        decoder_attention_mask = random_attention_mask([batch_size, 4])
        inputs = {
            "pixel_values": pixel_values,
            "decoder_input_ids": decoder_input_ids,
            "decoder_attention_mask": decoder_attention_mask,
        }

        return model, inputs

    def check_encoder_decoder_model_output_attentions(
        self,
        config,
        decoder_config,
        decoder_input_ids,
        decoder_attention_mask,
        labels=None,
        pixel_values=None,
        **kwargs,
    ):
        # make the decoder inputs a different shape from the encoder inputs to harden the test
        decoder_input_ids = decoder_input_ids[:, :-1]
        decoder_attention_mask = decoder_attention_mask[:, :-1]
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        outputs_encoder_decoder = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            output_attentions=True,
        )

        encoder_attentions = outputs_encoder_decoder["encoder_attentions"]
        self.assertEqual(len(encoder_attentions), config.num_hidden_layers)

        # in DEiT, the seq_len equals the number of patches + 2 (we add 2 for the [CLS] and distillation tokens)
        image_size = to_2tuple(encoder_model.config.image_size)
        patch_size = to_2tuple(encoder_model.config.patch_size)
        num_patches = (image_size[1] // patch_size[1]) * (image_size[0] // patch_size[0])
        seq_len = num_patches + 2
        self.assertEqual(encoder_attentions[0].shape[-3:], (config.num_attention_heads, seq_len, seq_len))

        decoder_attentions = outputs_encoder_decoder["decoder_attentions"]
        num_decoder_layers = (
            decoder_config.num_decoder_layers
            if hasattr(decoder_config, "num_decoder_layers")
            else decoder_config.num_hidden_layers
        )
        self.assertEqual(len(decoder_attentions), num_decoder_layers)

        self.assertEqual(
            decoder_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, decoder_input_ids.shape[-1], decoder_input_ids.shape[-1]),
        )

        cross_attentions = outputs_encoder_decoder["cross_attentions"]
        self.assertEqual(len(cross_attentions), num_decoder_layers)

        cross_attention_input_seq_len = decoder_input_ids.shape[-1]
        self.assertEqual(
            cross_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, cross_attention_input_seq_len, seq_len),
        )

    def get_encoder_decoder_model(self, config, decoder_config):
        encoder_model = DeiTModel(config).set_train(False)
        decoder_model = BertLMHeadModel(decoder_config).set_train(False)
        return encoder_model, decoder_model

    def prepare_config_and_inputs(self):
        bert_model_tester = BertModelTester(self)
        deit_model_tester = DeiTModelTester(self)
        encoder_config_and_inputs = deit_model_tester.prepare_config_and_inputs()
        decoder_config_and_inputs = bert_model_tester.prepare_config_and_inputs_for_decoder()
        config, pixel_values, _ = encoder_config_and_inputs
        (
            decoder_config,
            decoder_input_ids,
            decoder_token_type_ids,
            decoder_input_mask,
            decoder_sequence_labels,
            decoder_token_labels,
            decoder_choice_labels,
            encoder_attention_mask,
            _,
        ) = decoder_config_and_inputs

        # make sure that cross attention layers are added
        decoder_config.add_cross_attention = True
        return {
            "config": config,
            "pixel_values": pixel_values,
            "decoder_config": decoder_config,
            "decoder_input_ids": decoder_input_ids,
            "decoder_token_type_ids": decoder_token_type_ids,
            "decoder_attention_mask": decoder_input_mask,
            "decoder_sequence_labels": decoder_sequence_labels,
            "decoder_token_labels": decoder_token_labels,
            "decoder_choice_labels": decoder_choice_labels,
            "labels": decoder_token_labels,
        }


@require_mindspore
class ViT2BertModelTest(EncoderDecoderMixin, unittest.TestCase):
    def get_pretrained_model_and_inputs(self):
        model = VisionEncoderDecoderModel.from_encoder_decoder_pretrained(
            encoder_pretrained_model_name_or_path="hf-internal-testing/tiny-random-vit",
            decoder_pretrained_model_name_or_path="hf-internal-testing/tiny-bert"
=======
class ViT2BertModelTest(EncoderDecoderMixin, unittest.TestCase):
    def get_pretrained_model_and_inputs(self):
        model = VisionEncoderDecoderModel.from_encoder_decoder_pretrained(
            encoder_pretrained_model_name_or_path="hf-internal-testing/tiny-random-vit", decoder_pretrained_model_name_or_path="hf-internal-testing/tiny-bert"
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        )
        batch_size = 13
        pixel_values = floats_tensor(
            [
                batch_size,
                model.encoder.config.num_channels,
                model.encoder.config.image_size,
                model.encoder.config.image_size,
            ]
        )
<<<<<<< HEAD
        # for ViT, the sequence length is equal to the number of patches + 1 (for the [CLS] token)
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
        decoder_input_ids = ids_tensor([batch_size, 4], model.decoder.config.vocab_size)
        decoder_attention_mask = random_attention_mask([batch_size, 4])
        inputs = {
            "pixel_values": pixel_values,
            "decoder_input_ids": decoder_input_ids,
            "decoder_attention_mask": decoder_attention_mask,
        }

        return model, inputs

    def get_encoder_decoder_model(self, config, decoder_config):
        encoder_model = ViTModel(config).set_train(False)
        decoder_model = BertLMHeadModel(decoder_config).set_train(False)
        return encoder_model, decoder_model

    def prepare_config_and_inputs(self):
        vit_model_tester = ViTModelTester(self)
        bert_model_tester = BertModelTester(self)
        encoder_config_and_inputs = vit_model_tester.prepare_config_and_inputs()
        decoder_config_and_inputs = bert_model_tester.prepare_config_and_inputs_for_decoder()

        config, pixel_values, _ = encoder_config_and_inputs

        (
            decoder_config,
            decoder_input_ids,
            decoder_token_type_ids,
            decoder_input_mask,
            decoder_sequence_labels,
            decoder_token_labels,
            decoder_choice_labels,
            encoder_attention_mask,
            _,
        ) = decoder_config_and_inputs

        # make sure that cross attention layers are added
        decoder_config.add_cross_attention = True
        return {
            "config": config,
            "pixel_values": pixel_values,
            "decoder_config": decoder_config,
            "decoder_input_ids": decoder_input_ids,
            "decoder_token_type_ids": decoder_token_type_ids,
            "decoder_attention_mask": decoder_input_mask,
            "decoder_sequence_labels": decoder_sequence_labels,
            "decoder_token_labels": decoder_token_labels,
            "decoder_choice_labels": decoder_choice_labels,
            "labels": decoder_token_labels,
        }


@require_mindspore
class Swin2BartModelTest(EncoderDecoderMixin, unittest.TestCase):
    def get_encoder_decoder_model(self, config, decoder_config):
        encoder_model = SwinModel(config).set_train(False)
        decoder_model = BartForCausalLM(decoder_config).set_train(False)
        return encoder_model, decoder_model

    def prepare_config_and_inputs(self):
        model_tester_encoder = SwinModelTester(self, batch_size=13, embed_dim=32)
        model_tester_decoder = BartModelTester(self, batch_size=13, hidden_size=32, max_position_embeddings=512)
        encoder_config_and_inputs = model_tester_encoder.prepare_config_and_inputs()
        decoder_config_and_inputs = model_tester_decoder.prepare_config_and_inputs()
        config, pixel_values, _ = encoder_config_and_inputs
        decoder_config, decoder_inputs_dict = decoder_config_and_inputs
        decoder_inputs_dict["labels"] = decoder_inputs_dict["decoder_input_ids"]

        # make sure that cross attention layers are added
        decoder_config.add_cross_attention = True
        #  disable cache for now
        decoder_config.use_cache = False
        return {
            "config": config,
            "pixel_values": pixel_values,
            "decoder_config": decoder_config,
            **decoder_inputs_dict,
        }

    def check_encoder_decoder_model_output_attentions(
        self,
        config,
        decoder_config,
        decoder_input_ids,
        decoder_attention_mask,
        labels=None,
        pixel_values=None,
        **kwargs,
    ):
        # make the decoder inputs a different shape from the encoder inputs to harden the test
        decoder_input_ids = decoder_input_ids[:, :-1]
        decoder_attention_mask = decoder_attention_mask[:, :-1]
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        outputs_encoder_decoder = enc_dec_model(
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            output_attentions=True,
        )

        encoder_attentions = outputs_encoder_decoder["encoder_attentions"]
        self.assertEqual(len(encoder_attentions), config.num_hidden_layers)

        # in Swin, the seq_len equals:
        seq_len = encoder_model.config.window_size**2
        self.assertEqual(encoder_attentions[0].shape[-3:], (config.num_attention_heads[0], seq_len, seq_len))

        decoder_attentions = outputs_encoder_decoder["decoder_attentions"]
        num_decoder_layers = (
            decoder_config.num_decoder_layers
            if hasattr(decoder_config, "num_decoder_layers")
            else decoder_config.num_hidden_layers
        )
        self.assertEqual(len(decoder_attentions), num_decoder_layers)

        self.assertEqual(
            decoder_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, decoder_input_ids.shape[-1], decoder_input_ids.shape[-1]),
        )

        cross_attentions = outputs_encoder_decoder["cross_attentions"]
        self.assertEqual(len(cross_attentions), num_decoder_layers)

        encoder_seq_len = ((config.image_size // config.patch_size) ** 2) // (4 ** (len(config.depths) - 1))
        cross_attention_input_seq_len = decoder_input_ids.shape[-1]
        self.assertEqual(
            cross_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, cross_attention_input_seq_len, encoder_seq_len),
        )

    # there are no published pretrained BART-causal checkpoints for now
    def test_real_model_save_load_from_pretrained(self):
        pass


<<<<<<< HEAD
@require_mindspore
class ViT2TrOCR(EncoderDecoderMixin, unittest.TestCase):
    def get_encoder_decoder_model(self, config, decoder_config):
        encoder_model = ViTModel(config).set_train(False)
        decoder_model = TrOCRForCausalLM(decoder_config).set_train(False)
        return encoder_model, decoder_model

    def prepare_config_and_inputs(self):
        model_tester_encoder = ViTModelTester(self, batch_size=13)
        model_tester_decoder = TrOCRStandaloneDecoderModelTester(
            self, batch_size=13, d_model=32, max_position_embeddings=512
        )
        encoder_config_and_inputs = model_tester_encoder.prepare_config_and_inputs()
        decoder_config_and_inputs = model_tester_decoder.prepare_config_and_inputs()
        config, pixel_values, _ = encoder_config_and_inputs
        (decoder_config, decoder_input_ids, decoder_attention_mask, _) = decoder_config_and_inputs

        # make sure that cross attention layers are added
        decoder_config.add_cross_attention = True
        #  disable cache for now
        decoder_config.use_cache = False
        return {
            "config": config,
            "pixel_values": pixel_values,
            "decoder_config": decoder_config,
            "decoder_input_ids": decoder_input_ids,
            "decoder_attention_mask": decoder_attention_mask,
            "labels": decoder_input_ids,
        }

    # there are no published pretrained TrOCR checkpoints for now
    def test_real_model_save_load_from_pretrained(self):
        pass


@require_mindspore
class LayoutLMv32TrOCR(EncoderDecoderMixin, unittest.TestCase):
    def get_encoder_decoder_model(self, config, decoder_config):
        encoder_model = LayoutLMv3Model(config).set_train(False)
        decoder_model = TrOCRForCausalLM(decoder_config).set_train(False)
        return encoder_model, decoder_model

    def prepare_config_and_inputs(self):
        model_tester_encoder = LayoutLMv3ModelTester(self, batch_size=13, image_size=4, patch_size=2)
        model_tester_decoder = TrOCRStandaloneDecoderModelTester(
            self, batch_size=13, d_model=32, max_position_embeddings=512
        )
        encoder_config_and_inputs = model_tester_encoder.prepare_config_and_inputs()
        decoder_config_and_inputs = model_tester_decoder.prepare_config_and_inputs()
        (
            config,
            input_ids,
            bbox,
            pixel_values,
            token_type_ids,
            input_mask,
            sequence_labels,
            token_labels,
        ) = encoder_config_and_inputs
        (decoder_config, decoder_input_ids, decoder_attention_mask, _) = decoder_config_and_inputs

        # make sure that cross attention layers are added
        decoder_config.add_cross_attention = True
        #  disable cache for now
        decoder_config.use_cache = False
        return {
            "config": config,
            "pixel_values": pixel_values,
            "input_ids": input_ids,
            "bbox": bbox,
            "decoder_config": decoder_config,
            "decoder_input_ids": decoder_input_ids,
            "decoder_attention_mask": decoder_attention_mask,
            "labels": decoder_input_ids,
        }

    def check_encoder_decoder_model_output_attentions(
        self,
        config,
        decoder_config,
        decoder_input_ids,
        decoder_attention_mask,
        input_ids,
        pixel_values,
        labels=None,
        **kwargs,
    ):
        # make the decoder inputs a different shape from the encoder inputs to harden the test
        decoder_input_ids = decoder_input_ids[:, :-1]
        decoder_attention_mask = decoder_attention_mask[:, :-1]
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)
        outputs_encoder_decoder = enc_dec_model(
            input_ids=input_ids,
            pixel_values=pixel_values,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            output_attentions=True,
            **kwargs,
        )

        encoder_attentions = outputs_encoder_decoder["encoder_attentions"]
        self.assertEqual(len(encoder_attentions), config.num_hidden_layers)

        # LayoutLMv3's sequence length equals the number of text tokens + number of patches + 1 (we add 1 for the CLS token)
        text_seq_length = input_ids.shape[-1]
        image_seq_length = (encoder_model.config.input_size // encoder_model.config.patch_size) ** 2 + 1
        seq_len = text_seq_length + image_seq_length

        decoder_attentions = outputs_encoder_decoder["decoder_attentions"]
        num_decoder_layers = (
            decoder_config.num_decoder_layers
            if hasattr(decoder_config, "num_decoder_layers")
            else decoder_config.num_hidden_layers
        )
        self.assertEqual(len(decoder_attentions), num_decoder_layers)

        self.assertEqual(
            decoder_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, decoder_input_ids.shape[-1], decoder_input_ids.shape[-1]),
        )

        cross_attentions = outputs_encoder_decoder["cross_attentions"]
        self.assertEqual(len(cross_attentions), num_decoder_layers)

        cross_attention_input_seq_len = decoder_input_ids.shape[-1]
        self.assertEqual(
            cross_attentions[0].shape[-3:],
            (decoder_config.num_attention_heads, cross_attention_input_seq_len, seq_len),
        )

    def check_encoder_decoder_model_generate(self, config, decoder_config, pixel_values=None, **kwargs):
        encoder_model, decoder_model = self.get_encoder_decoder_model(config, decoder_config)
        enc_dec_model = VisionEncoderDecoderModel(encoder=encoder_model, decoder=decoder_model)

        # Generate until max length
        if hasattr(enc_dec_model.config, "eos_token_id"):
            enc_dec_model.config.eos_token_id = None
        if hasattr(enc_dec_model.config, "decoder") and hasattr(enc_dec_model.config.decoder, "eos_token_id"):
            enc_dec_model.config.decoder.eos_token_id = None
        if hasattr(enc_dec_model.generation_config, "eos_token_id"):
            enc_dec_model.generation_config.eos_token_id = None

        generated_output = enc_dec_model.generate(
            pixel_values=pixel_values,
            decoder_start_token_id=enc_dec_model.config.decoder.bos_token_id,
            **kwargs,
        )
        self.assertEqual(generated_output.shape, (pixel_values.shape[0],) + (decoder_config.max_length,))

    @unittest.skip("There are no published pretrained TrOCR checkpoints for now")
    def test_real_model_save_load_from_pretrained(self):
        pass


@require_vision
@require_mindspore
class TrOCRModelIntegrationTest(unittest.TestCase):
    @cached_property
    def default_processor(self):
        return TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten") if is_vision_available() else None

    @slow
    def test_inference_handwritten(self):
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

        dataset = load_dataset("hf-internal-testing/fixtures_ocr", split="test")
        image = Image.open(dataset[0]["file"]).convert("RGB")

        processor = self.default_processor
        pixel_values = processor(images=image, return_tensors="ms").pixel_values

        # forward pass
        decoder_input_ids = ms.tensor([[model.config.decoder.decoder_start_token_id]])
        outputs = model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)
        logits = outputs.logits

        # verify the logits
        expected_shape = (1, 1, model.decoder.config.vocab_size)
        self.assertEqual(outputs.logits.shape, expected_shape)

        expected_slice = ms.tensor(
            [-1.4502, -4.6683, -0.5347, -2.9291, 9.1435, -3.0571, 8.9764, 1.7560, 8.7358, -1.5311]
        )

        self.assertTrue(np.allclose(logits[0, 0, :10].asnumpy(), expected_slice.asnumpy(), atol=1e-4))

    @slow
    def test_inference_printed(self):
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")

        dataset = load_dataset("hf-internal-testing/fixtures_ocr", split="test")
        image = Image.open(dataset[1]["file"]).convert("RGB")

        processor = self.default_processor
        pixel_values = processor(images=image, return_tensors="ms").pixel_values

        # forward pass
        decoder_input_ids = ms.tensor([[model.config.decoder.decoder_start_token_id]])
        outputs = model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)
        logits = outputs.logits

        # verify the logits
        expected_shape = (1, 1, model.decoder.config.vocab_size)
        self.assertEqual(outputs.logits.shape, expected_shape)

        is_pillow_less_than_9 = version.parse(PIL.__version__) < version.parse("9.0.0")

        if is_pillow_less_than_9:
            expected_slice = ms.tensor(
                [-5.6816, -5.8388, 1.1398, -6.9034, 6.8505, -2.4393, 1.2284, -1.0232, -1.9661, -3.9210]
            )
        else:
            expected_slice = ms.tensor(
                [-5.6844, -5.8372, 1.1518, -6.8984, 6.8587, -2.4453, 1.2347, -1.0241, -1.9649, -3.9109]
            )

        self.assertTrue(np.allclose(logits[0, 0, :10].asnumpy(), expected_slice.asnumpy(), atol=1e-4))


=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
@require_vision
@require_mindspore
class ViT2GPT2ModelIntegrationTest(unittest.TestCase):
    @slow
    def test_inference_coco_en(self):
        loc = "ydshieh/vit-gpt2-coco-en"

        image_processor = ViTImageProcessor.from_pretrained(loc)
        tokenizer = GPT2Tokenizer.from_pretrained(loc)
        model = VisionEncoderDecoderModel.from_pretrained(loc)
        model.set_train(False)

        # We will verify our results on an image of cute cats
        img = Image.open("./tests/fixtures/tests_samples/COCO/000000039769.png")
        pixel_values = image_processor(images=img, return_tensors="ms").pixel_values

<<<<<<< HEAD
        decoder_input_ids = ms.tensor([[model.config.decoder_start_token_id]])

        logits = model(pixel_values, decoder_input_ids)[0].asnumpy()
=======
        decoder_input_ids = mindspore.tensor([[model.config.decoder_start_token_id]])

        logits = model(pixel_values, decoder_input_ids)[0].copy().numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d

        # verify the logits
        expected_shape = (1, 1, model.config.decoder.vocab_size)
        self.assertEqual(logits.shape, expected_shape)

        EXPECTED_LOGIT_SLICE = np.array(
            [
                -38.705807,
                -30.639929,
                -31.41903,
                -39.012012,
                -38.38696,
                -34.887207,
                -33.290855,
                -35.68447,
                -38.508484,
                -36.124645,
            ]
        )
        max_diff = np.amax(np.abs(logits[0, 0, :10] - EXPECTED_LOGIT_SLICE))
        self.assertLessEqual(max_diff, 1e-4)

        def generate_step(pixel_values):
            outputs = model.generate(
                pixel_values, max_length=16, num_beams=4, return_dict_in_generate=True, output_scores=True
            )
            output_ids = outputs.sequences
            preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
            preds = [pred.strip() for pred in preds]

<<<<<<< HEAD
            return preds, outputs.sequences_scores.asnumpy()
=======
            return preds, outputs.sequences_scores.copy().numpy()
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d

        preds, scores = generate_step(pixel_values)

        EXPECTED_SCORES = np.array([-0.5956343])
        max_diff = np.amax(np.abs(scores - EXPECTED_SCORES))
        self.assertLessEqual(max_diff, 1e-4)

        # should produce
        # ["a cat laying on top of a couch next to another cat"]
        self.assertEqual(preds, ["a cat laying on top of a couch next to another cat"])
<<<<<<< HEAD


@require_vision
@require_mindspore
@require_sentencepiece
class DonutModelIntegrationTest(unittest.TestCase):
    @slow
    def test_inference_docvqa(self):
        processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
        model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")

        dataset = load_dataset("hf-internal-testing/example-documents", split="test")
        image = dataset[0]["image"]

        pixel_values = processor(images=image, return_tensors="ms").pixel_values
        decoder_input_ids = processor.tokenizer(
            "<s_docvqa>", add_special_tokens=False, return_tensors="ms"
        ).input_ids

        # step 1: single forward pass
        outputs = model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)
        logits = outputs.logits

        # verify the logits
        expected_shape = (1, 1, 57532)
        self.assertEqual(outputs.logits.shape, expected_shape)

        expected_slice = ms.tensor([24.3873, -6.4491, 32.5394])
        self.assertTrue(np.allclose(logits[0, 0, :3].asnumpy(), expected_slice.asnumpy(), atol=1e-4))

        # step 2: generation
        task_prompt = "<s_docvqa><s_question>{user_input}</s_question><s_answer>"
        question = "When is the coffee break?"
        prompt = task_prompt.replace("{user_input}", question)
        decoder_input_ids = processor.tokenizer(prompt, add_special_tokens=False, return_tensors="ms").input_ids
        decoder_input_ids = decoder_input_ids

        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            output_scores=True,
            return_dict_in_generate=True,
        )
        sequence = processor.batch_decode(outputs.sequences)[0]
        sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token

        # verify generated sequence
        self.assertEqual(
            sequence, "<s_question> When is the coffee break?</s_question><s_answer> 11-14 to 11:39 a.m.</s_answer>"
        )

        # verify scores
        self.assertEqual(len(outputs.scores), 11)
        self.assertTrue(
            np.allclose(
                outputs.scores[0][0, :3].asnumpy(), ms.tensor([5.6019, -3.5070, 13.7123]).asnumpy(), atol=1e-4
            )
        )

    @slow
    def test_inference_cordv2(self):
        processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
        model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")

        dataset = load_dataset("hf-internal-testing/example-documents", split="test")
        image = dataset[2]["image"]

        pixel_values = processor(images=image, return_tensors="ms").pixel_values
        decoder_input_ids = processor.tokenizer(
            "<s_cord-v2>", add_special_tokens=False, return_tensors="ms"
        ).input_ids

        # step 1: single forward pass
        outputs = model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)
        logits = outputs.logits

        # verify the logits
        expected_shape = (1, 1, model.decoder.config.vocab_size)
        self.assertEqual(outputs.logits.shape, expected_shape)

        expected_slice = ms.tensor([-27.4344, -3.2686, -19.3524])
        self.assertTrue(np.allclose(logits[0, 0, :3].asnumpy(), expected_slice.asnumpy(), atol=1e-4))

        # step 2: generation
        task_prompt = "<s_cord-v2>"
        decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="ms").input_ids
        decoder_input_ids = decoder_input_ids

        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            output_scores=True,
            return_dict_in_generate=True,
        )

        sequence = processor.batch_decode(outputs.sequences)[0]
        sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token

        # verify generated sequence
        expected_sequence = "<s_menu><s_nm> CINNAMON SUGAR</s_nm><s_unitprice> 17,000</s_unitprice><s_cnt> 1 x</s_cnt><s_price> 17,000</s_price></s_menu><s_sub_total><s_subtotal_price> 17,000</s_subtotal_price></s_sub_total><s_total><s_total_price> 17,000</s_total_price><s_cashprice> 20,000</s_cashprice><s_changeprice> 3,000</s_changeprice></s_total>"  # noqa: E231  # fmt: skip
        self.assertEqual(sequence, expected_sequence)

        # verify scores
        self.assertEqual(len(outputs.scores), 43)
        self.assertTrue(
            np.allclose(
                outputs.scores[0][0, :3].asnumpy(), ms.tensor([-27.4344, -3.2686, -19.3524]).asnumpy(), atol=1e-4
            )
        )

    @slow
    def test_inference_rvlcdip(self):
        processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-rvlcdip")
        model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-rvlcdip")

        dataset = load_dataset("hf-internal-testing/example-documents", split="test")
        image = dataset[1]["image"]

        pixel_values = processor(images=image, return_tensors="ms").pixel_values

        # step 1: single forward pass
        decoder_input_ids = processor.tokenizer(
            "<s_rvlcdip>", add_special_tokens=False, return_tensors="ms"
        ).input_ids
        outputs = model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)
        logits = outputs.logits

        # verify the logits
        expected_shape = (1, 1, model.decoder.config.vocab_size)
        self.assertEqual(outputs.logits.shape, expected_shape)

        expected_slice = ms.tensor([-17.6490, -4.8381, -15.7577])
        self.assertTrue(np.allclose(logits[0, 0, :3].asnumpy(), expected_slice.asnumpy(), atol=1e-4))

        # step 2: generation
        task_prompt = "<s_rvlcdip>"
        decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="ms").input_ids
        decoder_input_ids = decoder_input_ids

        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            output_scores=True,
            return_dict_in_generate=True,
        )

        sequence = processor.batch_decode(outputs.sequences)[0]
        sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token

        # verify generated sequence
        self.assertEqual(sequence, "<s_class><advertisement/></s_class>")

        # verify scores
        self.assertEqual(len(outputs.scores), 4)
        self.assertTrue(
            np.allclose(
                outputs.scores[0][0, :3].asnumpy(), ms.tensor([-17.6490, -4.8381, -15.7577]).asnumpy(), atol=1e-4
            )
        )


@require_mindspore
@require_vision
@slow
class NougatModelIntegrationTest(unittest.TestCase):
    @cached_property
    def default_processor(self):
        return NougatProcessor.from_pretrained("facebook/nougat-base") if is_vision_available() else None

    @cached_property
    def default_model(self):
        return VisionEncoderDecoderModel.from_pretrained("facebook/nougat-base")

    @cached_property
    def default_image(self):
        filepath = hf_hub_download(
            repo_id="hf-internal-testing/fixtures_docvqa", filename="nougat_pdf.png", repo_type="dataset"
        )
        image = Image.open(filepath).convert("RGB")
        return image

    def test_forward_pass(self):
        processor = self.default_processor
        model = self.default_model
        image = self.default_image
        pixel_values = processor(images=image, return_tensors="ms").pixel_values

        decoder_input_ids = ms.tensor([[0]])
        outputs = model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)
        logits = outputs.logits

        # verify the logits
        expected_shape = (1, 1, model.decoder.config.vocab_size)
        self.assertEqual(outputs.logits.shape, expected_shape)

        # huggingface原本的期待结果
        # expected_slice = ms.tensor(
        #     [1.6253, -4.2179, 5.8532, -2.7911, -5.0609, -4.7397, -4.2890, -5.1073, -4.8908, -4.9729]
        # )
        # huggingface实际输出的结果
        expected_slice = ms.tensor(
            [0.7812, -5.6839, 6.3484, -2.6369, -3.7134, -3.5299, -3.0473, -3.7149, -3.9121, -4.0573]
        )
        self.assertTrue(np.allclose(logits[0, 0, :10].asnumpy(), expected_slice.asnumpy(), atol=1e-4))

    def test_generation(self):
        processor = self.default_processor
        model = self.default_model
        image = self.default_image
        pixel_values = processor(images=image, return_tensors="ms").pixel_values

        outputs = model.generate(
            pixel_values,
            min_length=1,
            max_length=3584,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
            output_scores=True,
        )

        # verify generated sequence
        generated = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0]
        # expected_raw_generation和huggingface的输出结果对齐
        expected_raw_generation = "# Nougat: Neural Optical Understanding for Academic Documents\n\n Lukas Blecher\n\nCorrespondence to: lblecher@meta.com\n\nGuillem Cucurull\n\nThomas Scialom\n\nRobert Stojnic\n\nMeta AI\n\n###### Abstract\n\nScientific knowledge is predominantly stored in books and scientific journals, often in the form of PDFs. However, the PDF format leads to a loss of semantic information, particularly for mathematical expressions. We propose Nougat (**N**eural **O**ptical **U**nderstanding for **A**cademic Documents), a Visual Transformer model that performs an _Optical Character Recognition_ (OCR) task for processing scientific documents into a markup language, and demonstrate the effectiveness of our model on a new dataset of scientific documents. The proposed approach offers a promising solution to enhance the accessibility of scientific knowledge in the digital age, by bridging the gap between human-readable documents and machine-readable text. We release the models and code to accelerate future work on scientific text recognition.\n\n## 1 Introduction\n\nThe majority of scientific knowledge is stored in books or published in scientific journals, most commonly in the Portable Document Format (PDF). Next to HTML, PDFs are the second most prominent data format on the internet, making up 2.4% of common crawl [1]. However, the information stored in these files is very difficult to extract into any other formats. This is especially true for highly specialized documents, such as scientific research papers, where the semantic information of mathematical expressions is lost.\n\nExisting Optical Character Recognition (OCR) engines, such as Tesseract OCR [2], excel at detecting and classifying individual characters and words in an image, but fail to understand the relationship between them due to their line-by-line approach. This means that they treat superscripts and subscripts in the same way as the surrounding text, which is a significant drawback for mathematical expressions. In mathematical notations like fractions, exponents, and matrices, relative positions of characters are crucial.\n\nConverting academic research papers into machine-readable text also enables accessibility and searchability of science as a whole. The information of millions of academic papers can not be fully accessed because they are locked behind an unreadable format. Existing corpora, such as the S2ORC dataset [3], capture the text of 12M2 papers using GROBID [4], but are missing meaningful representations of the mathematical equations.\n\nFootnote 2: The paper reports 8.1M papers but the authors recently updated the numbers on the GitHub page https://github.com/allenai/s2orc\n\nTo this end, we introduce Nougat, a transformer based model that can convert images of document pages to formatted markup text.\n\nThe primary contributions in this paper are\n\n* Release of a pre-trained model capable of converting a PDF to a lightweight markup language. We release the code and the model on GitHub3 Footnote 3: https://github.com/facebookresearch/nougat\n* We introduce a pipeline to create dataset for pairing PDFs to source code\n* Our method is only dependent on the image of a page, allowing access to scanned papers and books"
        self.assertTrue(generated == expected_raw_generation)

        # verify postprocessed sequence
        generated = processor.post_process_generation(generated, fix_markdown=False)
        # expected_generation和huggingface的输出结果对齐
        expected_generation = "\n\n# Nougat: Neural Optical Understanding for Academic Documents\n\n Lukas Blecher\n\nCorrespondence to: lblecher@meta.com\n\nGuillem Cucurull\n\nThomas Scialom\n\nRobert Stojnic\n\nMeta AI\n\n###### Abstract\n\nScientific knowledge is predominantly stored in books and scientific journals, often in the form of PDFs. However, the PDF format leads to a loss of semantic information, particularly for mathematical expressions. We propose Nougat (**N**eural **O**ptical **U**nderstanding for **A**cademic Documents), a Visual Transformer model that performs an _Optical Character Recognition_ (OCR) task for processing scientific documents into a markup language, and demonstrate the effectiveness of our model on a new dataset of scientific documents. The proposed approach offers a promising solution to enhance the accessibility of scientific knowledge in the digital age, by bridging the gap between human-readable documents and machine-readable text. We release the models and code to accelerate future work on scientific text recognition.\n\n## 1 Introduction\n\nThe majority of scientific knowledge is stored in books or published in scientific journals, most commonly in the Portable Document Format (PDF). Next to HTML, PDFs are the second most prominent data format on the internet, making up 2.4% of common crawl [1]. However, the information stored in these files is very difficult to extract into any other formats. This is especially true for highly specialized documents, such as scientific research papers, where the semantic information of mathematical expressions is lost.\n\nExisting Optical Character Recognition (OCR) engines, such as Tesseract OCR [2], excel at detecting and classifying individual characters and words in an image, but fail to understand the relationship between them due to their line-by-line approach. This means that they treat superscripts and subscripts in the same way as the surrounding text, which is a significant drawback for mathematical expressions. In mathematical notations like fractions, exponents, and matrices, relative positions of characters are crucial.\n\nConverting academic research papers into machine-readable text also enables accessibility and searchability of science as a whole. The information of millions of academic papers can not be fully accessed because they are locked behind an unreadable format. Existing corpora, such as the S2ORC dataset [3], capture the text of 12M2 papers using GROBID [4], but are missing meaningful representations of the mathematical equations.\n\nFootnote 2: The paper reports 8.1M papers but the authors recently updated the numbers on the GitHub page https://github.com/allenai/s2orc\n\nTo this end, we introduce Nougat, a transformer based model that can convert images of document pages to formatted markup text.\n\nThe primary contributions in this paper are\n\n* Release of a pre-trained model capable of converting a PDF to a lightweight markup language. We release the code and the model on GitHub3 Footnote 3: https://github.com/facebookresearch/nougat\n* We introduce a pipeline to create dataset for pairing PDFs to source code\n* Our method is only dependent on the image of a page, allowing access to scanned papers and books"
        self.assertTrue(generated == expected_generation)

        # verify scores
        # len(outputs.scores)和huggingface的输出结果对齐
        self.assertEqual(len(outputs.scores), 705)
        # ms.tensor()和huggingface的输出结果对齐
        self.assertTrue(
            np.allclose(
                outputs.scores[0][0, :3].asnumpy(), ms.tensor([0.7812, -5.6839, 6.3484]).asnumpy(), atol=1e-4
            )
        )
=======
>>>>>>> 92b2bcf66e16da01a6be2ef2e1b1e69ef6bed11d
