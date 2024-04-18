# Copyright 2023-present the HuggingFace Inc. team.
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

import warnings
from typing import Any, List, Optional

import mindspore
from mindspore import nn, ops, Parameter, Tensor
from mindnlp.transformers.ms_utils import Conv1D

from .tuners_utils import BaseTunerLayer, check_adapters_to_merge
from ..utils import transpose
from mindnlp.abc import  ParameterDict
from mindspore.common.initializer import initializer,  Constant


class IA3Layer(BaseTunerLayer):
    # All names of layers that may contain adapter weights
    adapter_layer_names = ("ia3_l",)

    def __init__(self, base_layer: nn.Cell, is_feedforward: bool, **kwargs) -> None:
        self.base_layer = base_layer
        self.ia3_l = ParameterDict({})
        # Mark the weight as unmerged
        self._disable_adapters = False
        self.merged_adapters = []
        self.is_feedforward = is_feedforward

        base_layer = self.get_base_layer() 
        if isinstance(base_layer, nn.Dense):
            in_features, out_features = base_layer.in_features, base_layer.out_features
        elif isinstance(base_layer, nn.Conv2d):
            in_features, out_features = base_layer.in_channels, base_layer.out_channels
        elif isinstance(base_layer, nn.Embedding):
            in_features, out_features = base_layer.vocab_size, base_layer.embedding_size
        elif isinstance(base_layer, Conv1D):
            in_features, out_features = (
                base_layer.weight.ds_shape if hasattr(base_layer.weight, "ds_shape") else base_layer.weight.shape
            )
        else:
            raise ValueError(f"Unsupported layer type {type(base_layer)}")
        self.in_features = in_features
        self.out_features = out_features

    def update_layer(self, adapter_name, init_ia3_weights):
        # This code works for linear layers, override for other layer types
        # Actual trainable parameters
        if self.is_feedforward:
            weight = ops.randn((1, self.in_features))
        else:
            weight = ops.randn((self.out_features, 1))
        self.ia3_l[adapter_name] = Parameter(weight)
        if init_ia3_weights:
            self.reset_ia3_parameters(adapter_name)
        self.set_adapter(self.active_adapters) 

    def reset_ia3_parameters(self, adapter_name):
        if adapter_name in self.ia3_l.keys():
            # initialize learned vector with torch.ones
            self.ia3_l[adapter_name].set_data(initializer(
                Constant(1.0),
                self.ia3_l[adapter_name].shape,
                self.ia3_l[adapter_name].dtype
            ))


class Linear(nn.Cell, IA3Layer):
    # (IA)^3 implemented in a dense layer
    def __init__(
        self,
        base_layer: nn.Cell,
        adapter_name: str,
        fan_in_fan_out: bool = False,  # Set this to True if the layer to replace stores weight like (fan_in, fan_out)
        is_feedforward: bool = False,  # Set to True if the layer is treated as a feedforward layer
        is_target_conv_1d_layer: bool = False,  # whether target module is a conv1d layer. useful while unloading later
        init_ia3_weights: bool = True,  # whether to initialize IA3 weights
        **kwargs,
    ) -> None:
        super().__init__()
        IA3Layer.__init__(self, base_layer, is_feedforward=is_feedforward)
        self.fan_in_fan_out = fan_in_fan_out
        self.is_target_conv_1d_layer = is_target_conv_1d_layer
        self._active_adapter = adapter_name
        self.update_layer(adapter_name, init_ia3_weights)

    def merge(self, safe_merge: bool = False, adapter_names: Optional[List[str]] = None) -> None:
        """
        Merge the active adapter weights into the base weights

        Args:
            safe_merge (`bool`, *optional*):
                If True, the merge operation will be performed in a copy of the original weights and check for NaNs
                before merging the weights. This is useful if you want to check if the merge operation will produce
                NaNs. Defaults to `False`.
            adapter_names (`List[str]`, *optional*):
                The list of adapter names that should be merged. If None, all active adapters will be merged. Defaults
                to `None`.
        """
        adapter_names = check_adapters_to_merge(self, adapter_names)
        if not adapter_names:
            # no adapter to merge
            return

        for active_adapter in adapter_names:
            if active_adapter in self.ia3_l.keys():
                base_layer = self.get_base_layer() 
                ia3_l = transpose(self.ia3_l[active_adapter].data, self.fan_in_fan_out)
                if safe_merge:
                    orig_weights = base_layer.weight.data
                    orig_weights = ops.mul(orig_weights, ia3_l)

                    if not ops.isfinite(orig_weights).all():
                        raise ValueError(
                            f"NaNs detected in the merged weights. The adapter {active_adapter} seems to be broken"
                        )
                    base_layer.weight.data = orig_weights
                else:
                    base_layer.weight.data = ops.mul(base_layer.weight.data, ia3_l)

                if not self.is_feedforward and (base_layer.bias is not None):
                    scaling = self.ia3_l[active_adapter].reshape(base_layer.bias.shape)
                    base_layer.bias.data = ops.mul(base_layer.bias.data, scaling.data)

                self.merged_adapters.append(active_adapter)

    def unmerge(self) -> None:
        """
        This method unmerges all merged adapter layers from the base weights.
        """
        if not self.merged:
            warnings.warn("Already unmerged. Nothing to do.")
            return

        warnings.warn("Unmerge result can be inaccurate for (IA)^3.")
        while len(self.merged_adapters) > 0:
            active_adapter = self.merged_adapters.pop()
            if active_adapter in self.ia3_l.keys():
                base_layer = self.get_base_layer()
                # Add tolerace to avoid division by zero
                ia3_l = transpose(self.ia3_l[active_adapter].data, self.fan_in_fan_out) + 1e-8
                base_layer.weight.data = ops.div(base_layer.weight.data, ia3_l)

                if not self.is_feedforward and (base_layer.bias is not None):
                    scaling = self.ia3_l[active_adapter].reshape(base_layer.bias.shape)
                    base_layer.bias.data = ops.div(base_layer.bias.data, scaling.data + 1e-8)

    def construct(self, x: Tensor, *args: Any, **kwargs: Any) -> Tensor:
        dtype = previous_dtype = x.dtype

        if self.disable_adapters:
            if self.merged:
                self.unmerge()
            result = self.base_layer(x, *args, **kwargs)
        elif self.merged:
            result = self.base_layer(x, *args, **kwargs)
        else:
            ia3_scaling = 1
            for active_adapter in self.active_adapters:
                if active_adapter not in self.ia3_l.keys():
                    continue
                dtype = self.ia3_l[active_adapter].dtype
                ia3_scaling *= self.ia3_l[active_adapter].flatten()

            if self.is_feedforward:
                x = x.to(dtype)
                # TODO: weight.dtype can be != self.ia3_l[self.active_adapters].dtype
                # e.g. bf16 vs fp32. Is that okay?
                interm = (x * ia3_scaling).to(self.get_base_layer().weight.dtype)
                result = self.base_layer(interm, *args, **kwargs)
            else:
                result = self.base_layer(x, *args, **kwargs)
                result = result.to(dtype) * ia3_scaling

        result = result.to(previous_dtype)
        return result


class Conv2d(nn.Cell, IA3Layer):
    def __init__(
        self,
        base_layer: nn.Cell,
        adapter_name: str,
        fan_in_fan_out: bool = False,  # Set this to True if the layer to replace stores weight like (fan_in, fan_out)
        is_feedforward: bool = False,  # Set to True if the layer is treated as a feedforward layer
        init_ia3_weights: bool = True,
        **kwargs,
    ) -> None:
        super().__init__()
        IA3Layer.__init__(self, base_layer, is_feedforward=is_feedforward)
        self.fan_in_fan_out = fan_in_fan_out
        self._active_adapter = adapter_name

        self.update_layer(adapter_name, init_ia3_weights)

    def update_layer(self, adapter_name, init_ia3_weights):
        # Actual trainable parameters
        if self.is_feedforward:
            weight = ops.randn((1, self.in_features, 1, 1))
        else:
            weight = ops.randn((1, self.out_features, 1, 1))
        self.ia3_l[adapter_name] = Parameter(weight)
        if init_ia3_weights:
            self.reset_ia3_parameters(adapter_name)
        self.set_adapter(self.active_adapters)

    def merge(self, safe_merge: bool = False, adapter_names: Optional[List[str]] = None) -> None:
        """
        Merge the active adapter weights into the base weights

        Args:
            safe_merge (`bool`, *optional*):
                If True, the merge operation will be performed in a copy of the original weights and check for NaNs
                before merging the weights. This is useful if you want to check if the merge operation will produce
                NaNs. Defaults to `False`.
            adapter_names (`List[str]`, *optional*):
                The list of adapter names that should be merged. If None, all active adapters will be merged. Defaults
                to `None`.
        """
        adapter_names = check_adapters_to_merge(self, adapter_names)
        if not adapter_names:
            # no adapter to merge
            return

        for active_adapter in adapter_names:
            if active_adapter in self.ia3_l.keys():
                base_layer = self.get_base_layer()
                ia3_scaling = self.ia3_l[active_adapter].data
                if not self.is_feedforward:
                    ia3_scaling = ia3_scaling.permute(1, 0, 2, 3)

                if safe_merge:
                    output_weight = ops.mul(base_layer.weight.data, ia3_scaling).clone()

                    if not ops.isfinite(output_weight).all():
                        raise ValueError(
                            f"NaNs detected in the merged weights. The adapter {active_adapter} seems to be broken"
                        )

                    base_layer.weight.data = output_weight
                else:
                    base_layer.weight.data = ops.mul(base_layer.weight.data, ia3_scaling)

                if not self.is_feedforward and (base_layer.bias is not None):
                    scaling = self.ia3_l[active_adapter].reshape(base_layer.bias.shape)
                    base_layer.bias.data = ops.mul(base_layer.bias.data, scaling.data)

                self.merged_adapters.append(active_adapter)

    def unmerge(self) -> None:
        """
        This method unmerges all merged adapter layers from the base weights.
        """
        if not self.merged:
            warnings.warn("Already unmerged. Nothing to do.")
            return

        warnings.warn("Unmerge result can be inaccurate for (IA)^3.")
        while len(self.merged_adapters) > 0:
            active_adapter = self.merged_adapters.pop()
            if active_adapter in self.ia3_l.keys():
                base_layer = self.get_base_layer()
                # divide by (IA)^3 vector. Add tolerace to avoid division by zero
                ia3_scaling = self.ia3_l[active_adapter].data
                if not self.is_feedforward:
                    ia3_scaling = ia3_scaling.permute(1, 0, 2, 3)
                base_layer.weight.data = ops.div(base_layer.weight.data, ia3_scaling + 1e-8)

                if not self.is_feedforward and (base_layer.bias is not None):
                    scaling = self.ia3_l[active_adapter].reshape(base_layer.bias.shape)
                    base_layer.bias.data = ops.mul(base_layer.bias.data, scaling.data)

    def construct(self, x: Tensor, *args: Any, **kwargs: Any) -> Tensor:
        dtype = previous_dtype = x.dtype

        if self.disable_adapters:
            if self.merged:
                self.unmerge()
            result = self.base_layer(x, *args, **kwargs)
        elif self.merged:
            result = self.base_layer(x, *args, **kwargs)
        else:
            ia3_scaling = 1
            for active_adapter in self.active_adapters:
                if active_adapter not in self.ia3_l.keys():
                    continue
                dtype = self.ia3_l[active_adapter].dtype
                ia3_scaling *= self.ia3_l[active_adapter]

            if self.is_feedforward:
                x = x.to(dtype)
                # TODO: weight.dtype can be != self.ia3_l[self.active_adapters].dtype
                # e.g. bf16 vs fp32. Is that okay?
                interm = (x * ia3_scaling).to(self.get_base_layer().weight.dtype)
                result = self.base_layer(interm, *args, **kwargs)
            else:
                result = self.base_layer(x, *args, **kwargs)
                result = result.to(dtype) * ia3_scaling

        result = result.to(previous_dtype)
        return result
