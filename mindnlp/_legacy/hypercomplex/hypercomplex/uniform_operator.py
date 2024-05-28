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
"""Uniform operators"""
from mindspore.nn import Cell


class _UniformOperator(Cell):
    r"""
    Base class for layers that operate with the second-order hypercomplex numbers, and are designed
    using the bridge pattern.

    Constructs the object of the 'hc_op' type, passing 'hc_impl' as a parameter.

    Args:
        hc_op (Type): The abstraction part of the bridge pattern.
        hc_impl (Type): The implementor part of the bridge pattern.
        **kwargs (dict): Additional arguments that may be required to construct the specific layer

    Inputs:
        - **inp** (Tensor) - input tensor. The shape is specific to the subclass.

    Outputs:
        Tensor of shape, which is specific to the subclass.

    Supported Platforms:
        ``Ascend`` ``GPU`` ``CPU``
    """

    def __init__(self,
                 hc_op,
                 hc_impl,
                 **kwargs) -> None:
        r"""
        Initializes an instance of the '_UniformOperator' class.
        
        Args:
            self: The instance of the class (automatically passed).
            hc_op: The class or function representing the high-level operation to be performed.
                   This parameter is required and must be a callable object.
            hc_impl: The object implementing the high-level operation.
                     This parameter is required and must be an instance of a class or a callable object.
            **kwargs: Additional keyword arguments that might be required by the 'hc_op' implementation.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            None.
        
        Note:
            This method initializes the instance by assigning the 'hc_op' and 'hc_impl' parameters
            to the instance attributes 'op' and 'hc_impl' respectively. These attributes can be accessed
            throughout the class to perform the desired high-level operation.
        
        Example:
            hc_op = HighLevelOperation()  # Create a high-level operation object
            hc_impl = HighLevelImplementation()  # Create a high-level implementation object
            
            uniform_operator = _UniformOperator(hc_op, hc_impl)  # Initialize the '_UniformOperator' instance
        """
        super().__init__()
        self.op = hc_op(hc_impl, **kwargs)

    def construct(self, x):
        r"""
        Construct a new instance of the _UniformOperator class.
        
        Args:
            self (_UniformOperator): The instance of the _UniformOperator class.
            x: The input value for the construction.
        
        Returns:
            None: This method returns None.
        
        Raises:
            This method does not raise any exceptions.
        """
        return self.op(x)
