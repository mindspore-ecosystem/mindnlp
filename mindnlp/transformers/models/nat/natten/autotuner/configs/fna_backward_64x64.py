#################################################################################################
# Copyright (c) 2022-2024 Ali Hassani.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#################################################################################################


from typing import Dict, List

from ...types import FnaTileShapeType


# NOTE: we're excluding tile shapes that include 1 just to
# reduce the giant number of configs down to a reasonable
# amount; otherwise autotuning would take more than a few
# seconds per call which is unacceptable. Tile shapes with
# 1s are rarely selected.

_FNA_BACKWARD_64x64_TILE_SIZES: Dict[int, List[FnaTileShapeType]] = {
    1: [
        ((64,), (64,)),
    ],
    2: [
        ((32, 2), (32, 2)),
        ((32, 2), (16, 4)),
        ((32, 2), (8, 8)),
        ((32, 2), (4, 16)),
        ((32, 2), (2, 32)),
        ((16, 4), (32, 2)),
        ((16, 4), (16, 4)),
        ((16, 4), (8, 8)),
        ((16, 4), (4, 16)),
        ((16, 4), (2, 32)),
        ((8, 8), (32, 2)),
        ((8, 8), (16, 4)),
        ((8, 8), (8, 8)),
        ((8, 8), (4, 16)),
        ((8, 8), (2, 32)),
        ((4, 16), (32, 2)),
        ((4, 16), (16, 4)),
        ((4, 16), (8, 8)),
        ((4, 16), (4, 16)),
        ((4, 16), (2, 32)),
        ((2, 32), (32, 2)),
        ((2, 32), (16, 4)),
        ((2, 32), (8, 8)),
        ((2, 32), (4, 16)),
        ((2, 32), (2, 32)),
    ],
    3: [
        ((16, 2, 2), (16, 2, 2)),
        ((16, 2, 2), (8, 4, 2)),
        ((16, 2, 2), (8, 2, 4)),
        ((16, 2, 2), (4, 8, 2)),
        ((16, 2, 2), (4, 4, 4)),
        ((16, 2, 2), (4, 2, 8)),
        ((16, 2, 2), (2, 16, 2)),
        ((16, 2, 2), (2, 8, 4)),
        ((16, 2, 2), (2, 4, 8)),
        ((16, 2, 2), (2, 2, 16)),
        ((8, 4, 2), (16, 2, 2)),
        ((8, 4, 2), (8, 4, 2)),
        ((8, 4, 2), (8, 2, 4)),
        ((8, 4, 2), (4, 8, 2)),
        ((8, 4, 2), (4, 4, 4)),
        ((8, 4, 2), (4, 2, 8)),
        ((8, 4, 2), (2, 16, 2)),
        ((8, 4, 2), (2, 8, 4)),
        ((8, 4, 2), (2, 4, 8)),
        ((8, 4, 2), (2, 2, 16)),
        ((8, 2, 4), (16, 2, 2)),
        ((8, 2, 4), (8, 4, 2)),
        ((8, 2, 4), (8, 2, 4)),
        ((8, 2, 4), (4, 8, 2)),
        ((8, 2, 4), (4, 4, 4)),
        ((8, 2, 4), (4, 2, 8)),
        ((8, 2, 4), (2, 16, 2)),
        ((8, 2, 4), (2, 8, 4)),
        ((8, 2, 4), (2, 4, 8)),
        ((8, 2, 4), (2, 2, 16)),
        ((4, 8, 2), (16, 2, 2)),
        ((4, 8, 2), (8, 4, 2)),
        ((4, 8, 2), (8, 2, 4)),
        ((4, 8, 2), (4, 8, 2)),
        ((4, 8, 2), (4, 4, 4)),
        ((4, 8, 2), (4, 2, 8)),
        ((4, 8, 2), (2, 16, 2)),
        ((4, 8, 2), (2, 8, 4)),
        ((4, 8, 2), (2, 4, 8)),
        ((4, 8, 2), (2, 2, 16)),
        ((4, 4, 4), (16, 2, 2)),
        ((4, 4, 4), (8, 4, 2)),
        ((4, 4, 4), (8, 2, 4)),
        ((4, 4, 4), (4, 8, 2)),
        ((4, 4, 4), (4, 4, 4)),
        ((4, 4, 4), (4, 2, 8)),
        ((4, 4, 4), (2, 16, 2)),
        ((4, 4, 4), (2, 8, 4)),
        ((4, 4, 4), (2, 4, 8)),
        ((4, 4, 4), (2, 2, 16)),
        ((4, 2, 8), (16, 2, 2)),
        ((4, 2, 8), (8, 4, 2)),
        ((4, 2, 8), (8, 2, 4)),
        ((4, 2, 8), (4, 8, 2)),
        ((4, 2, 8), (4, 4, 4)),
        ((4, 2, 8), (4, 2, 8)),
        ((4, 2, 8), (2, 16, 2)),
        ((4, 2, 8), (2, 8, 4)),
        ((4, 2, 8), (2, 4, 8)),
        ((4, 2, 8), (2, 2, 16)),
        ((2, 16, 2), (16, 2, 2)),
        ((2, 16, 2), (8, 4, 2)),
        ((2, 16, 2), (8, 2, 4)),
        ((2, 16, 2), (4, 8, 2)),
        ((2, 16, 2), (4, 4, 4)),
        ((2, 16, 2), (4, 2, 8)),
        ((2, 16, 2), (2, 16, 2)),
        ((2, 16, 2), (2, 8, 4)),
        ((2, 16, 2), (2, 4, 8)),
        ((2, 16, 2), (2, 2, 16)),
        ((2, 8, 4), (16, 2, 2)),
        ((2, 8, 4), (8, 4, 2)),
        ((2, 8, 4), (8, 2, 4)),
        ((2, 8, 4), (4, 8, 2)),
        ((2, 8, 4), (4, 4, 4)),
        ((2, 8, 4), (4, 2, 8)),
        ((2, 8, 4), (2, 16, 2)),
        ((2, 8, 4), (2, 8, 4)),
        ((2, 8, 4), (2, 4, 8)),
        ((2, 8, 4), (2, 2, 16)),
        ((2, 4, 8), (16, 2, 2)),
        ((2, 4, 8), (8, 4, 2)),
        ((2, 4, 8), (8, 2, 4)),
        ((2, 4, 8), (4, 8, 2)),
        ((2, 4, 8), (4, 4, 4)),
        ((2, 4, 8), (4, 2, 8)),
        ((2, 4, 8), (2, 16, 2)),
        ((2, 4, 8), (2, 8, 4)),
        ((2, 4, 8), (2, 4, 8)),
        ((2, 4, 8), (2, 2, 16)),
        ((2, 2, 16), (16, 2, 2)),
        ((2, 2, 16), (8, 4, 2)),
        ((2, 2, 16), (8, 2, 4)),
        ((2, 2, 16), (4, 8, 2)),
        ((2, 2, 16), (4, 4, 4)),
        ((2, 2, 16), (4, 2, 8)),
        ((2, 2, 16), (2, 16, 2)),
        ((2, 2, 16), (2, 8, 4)),
        ((2, 2, 16), (2, 4, 8)),
        ((2, 2, 16), (2, 2, 16)),
    ],
}
