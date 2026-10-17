import os
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # BLAS thread pools deadlock in the forked render workers; renders parallelize by process
from .gfx import *
from .board import Cam, Game, Look, View, draw_board, keyframes, sq_xy
from .edit import Edit
from . import audio
import chess
cv2.setNumThreads(1)
