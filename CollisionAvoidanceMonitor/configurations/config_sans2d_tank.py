from transform import Transformation
import os

# Config happens here:

# Colors for each body
MAGENTA = (1, 0, 1)
YELLOW = (1, 1, 0)
CYAN = (0, 1, 1)
GREEN = (0, 1, 0)

# Colors for each body
colors = [MAGENTA, YELLOW, CYAN, GREEN]

# PV prefix
pv_prefix = os.environ["MYPVPREFIX"]

# PV prefix for controlling the system
control_pv = "{}COLLIDE:".format(pv_prefix)

# Define the geometry of the system in mm
# Coordinate origin at arc centre, with nominal beam height
# Size is defined x, y, z (x is beam, z is up)

front_detector_to_front_baffle = 1050
front_baffle_to_rear_baffle = 210
rear_baffle_to_rear_detector = 350

object_y_z_size = 1000, 1000

front_baffle_width = 100  # Assumed
front_detector_width = 2 * (front_detector_to_front_baffle - front_baffle_width / 2)
rear_baffle_width = 2 * (front_baffle_to_rear_baffle - front_baffle_width / 2)
rear_detector_width = 2 * (rear_baffle_to_rear_detector - rear_baffle_width / 2)

print("Widths are {}, {}, {}, {}".format(front_detector_width, front_baffle_width, rear_baffle_width, rear_detector_width))

front_detector = dict(name="Front Detector", size=(front_detector_width, object_y_z_size[0], object_y_z_size[1]), color=MAGENTA)
front_baffle = dict(name="Front Baffle", size=(front_baffle_width, object_y_z_size[0], object_y_z_size[1]), color=YELLOW)
rear_baffle = dict(name="Rear Baffle", size=(rear_baffle_width, object_y_z_size[0], object_y_z_size[1]), color=CYAN)
rear_detector = dict(name="Rear Detector", size=(rear_detector_width, object_y_z_size[0], object_y_z_size[1]), color=GREEN)

# Define some search parameters
coarse = 20.0
fine = 0.5

# Define the oversized-ness of each body - a global value in mm
oversize = coarse / 4

# Put them in a list
geometries = [front_detector, front_baffle, rear_baffle, rear_detector]

ignore = []


def moves(axes):
    # Front Detector
    t = Transformation()
    t.translate(x=1585.00000 + axes[0])

    yield t

    # Front Baffle
    t = Transformation()
    t.translate(x=2884.00000 + axes[1])

    yield t

    # Rear Baffle
    t = Transformation()
    t.translate(x=12021.00000 + axes[2])

    yield t

    # Rear Detector
    t = Transformation()
    t.translate(x=12367.00000 + axes[3])

    yield t

# Attach monitors to readbacks
pvs = [
    "{}MOT:MTR0501",
    "{}MOT:MTR0503",
    "{}MOT:MTR0408",
    "{}MOT:MTR0401",
]

pvs = [pv.format(pv_prefix) for pv in pvs]

hardlimits = [
    [-100000, 100000],
    [-100000, 100000],
    [-100000, 100000],
    [-100000, 100000],
]
