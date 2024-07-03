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
KOSMOS-2 Model.
"""
from . import (
    configuration_kosmos2,
    modeling_kosmos2,
    processing_kosmos2,
)

from .configuration_kosmos2 import *
from .modeling_kosmos2 import *
from .processing_kosmos2 import *

__all__ = []
__all__.extend(configuration_kosmos2.__all__)
__all__.extend(modeling_kosmos2.__all__)
__all__.extend(processing_kosmos2.__all__)
