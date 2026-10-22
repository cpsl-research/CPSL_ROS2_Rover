# Developing CPSL_ROS2_Rover

For someone changing this fork. To install and drive, start at the [first tutorial](tutorials/01_first_drive.md).

## Layout

```
scripts/deps/rover.sh            apt dependencies; `--check` reports them without root (+ _common.sh)
src/roverrobotics_ros2/          vendored upstream packages (below)
  roverrobotics_driver/          C++ driver (src/, include/, library/librover), launch/, config/
  roverrobotics_description/     URDF, meshes, rviz
  roverrobotics_input_manager/   scripts/joys_manager.py and scripts/modules/
TODO.md                          known issues, ready to paste into an issue
```

The snapshot was imported in one commit (`f86b620`) with no upstream history and no
recorded upstream commit. Everything not listed in the next section is upstream code,
including the launch files and configs for the other models, which stay in place so that
diffs against upstream stay small.

## What the lab changed

Eight files differ from upstream on purpose. Seven come from two commits, and the eighth
from the import commit.

| File (under `roverrobotics_driver/` unless noted) | Change | Commit |
|---|---|---|
| `launch/pro.launch.py` | `namespace` argument; `GroupAction` with `PushRosNamespace`, `/tf` and `/tf_static` remapped to relative names; `robot_state_publisher` and `joint_state_publisher` inside the group | `69e9303` |
| `launch/pro_teleop.launch.py` | `namespace` argument, passed to both includes; `joy_dev` argument | `69e9303`, `f86b620` |
| `launch/ps4_controller.launch.py` | `namespace` argument and group; `joy_dev` argument for `joy_linux_node` | `69e9303`, `f86b620` |
| `config/pro_config.yaml` | Parameter key `/**/roverrobotics_driver`; relative topic names; `publish_tf: true` | `69e9303`, `3f4a0c4` |
| `config/topics.yaml` | `cmd_vel` made relative | `69e9303` |
| `../roverrobotics_input_manager/scripts/joys_manager.py` | subscribes to `joy`, not `/joy` | `69e9303` |
| `config/ps4_controller_config.yaml` | right stick rotates, not the left trigger; several axis indices changed (each marked in the file) | `f86b620` |

The idea is "no absolute names anywhere", so a namespace moves everything. Give any new topic a relative name.

Later lab commits delete files (the `bno055`, `rplidar_ros` and Gazebo packages), strip the
`rplidar` and `bno055` entries from `config/accessories.yaml` and `launch/accessories.launch.py`
(only `realsense` remains), or add `scripts/deps/`, `TODO.md` and these docs.

## Rebasing on upstream

Upstream is [RoverRobotics/roverrobotics_ros2](https://github.com/RoverRobotics/roverrobotics_ros2),
branch `jazzy`. On 2026-10-20 its head (`959193a`) differs from this snapshot in many
files beyond the eight above, so there is no shared history to `git rebase` onto.

1. Clone upstream `jazzy` next to this repo and compare the three package folders with
   `diff -ru`.
2. Take the upstream files you want. Then reapply the lab's eight files from the commits
   above: `git show 69e9303 3f4a0c4 f86b620 -- src/roverrobotics_ros2` (`f86b620` also
   imported a `build/` tree; ignore it).
3. Rebuild with a copy install, and check as below. Record the upstream commit you took in
   the commit message; this repo does not record one today.

## Symlink install versus copy install

Build with `colcon build` (copy install). With `--symlink-install`, colcon links
`joys_manager.py` into `install/`, and git stores it as mode `100644`, so the link target
is not executable: `ros2 launch` then reports `executable 'joys_manager.py' not found`.
Reproduced on 2026-10-20 in a scratch copy: after a symlink build `ros2 pkg executables
roverrobotics_input_manager` printed nothing; after a copy build the file was `-rwxr-xr-x`.
The likely fix, untested, is to commit the script as `100755` (`git update-index --chmod=+x`); see `TODO.md`.
A copy install also means every edit to a launch file or config needs a rebuild.

## Checking a change without a robot

There is one unit test (`test/test_pro_odometry.cpp`, run by `colcon test`); the rest has none.
These run on any machine with ROS installed:

```bash
for f in scripts/deps/*.sh; do bash -n "$f"; done
colcon build && source install/setup.bash
ros2 launch roverrobotics_driver pro_teleop.launch.py --show-args
ros2 launch roverrobotics_driver pro_teleop.launch.py namespace:=test   # then, in a second terminal:
ros2 node list; ros2 topic list     # expect /test/... names
```

With no robot the driver logs a fatal "Robot at /dev/rover-pro is not available" and is restarted every
second; the other nodes still start. That is enough to check names and `tf` remaps. If a
robot is plugged in at `/dev/rover-pro`, the launch opens it, so unplug it or stop other
programs using the port first.

## Pro wheel odometry calibration

The Pro's wheel odometry is three driver parameters in `config/pro_config.yaml`: `odom_linear_scale`
(multiplies linear and angular velocity; range 0.25 to 4.0), `odom_traction_factor` (angular; 0.1 to 2.0)
and `odom_wheel_separation` (m; 0.1 to 1.0). Without them the driver uses 1.0, 0.610 and 0.365, the
original constants; an out-of-range value is logged as an error and that one keeps its default. The
driver logs the effective values on start. `pro.launch.py` and `pro_teleop.launch.py` take optional
arguments of the same names; a non-empty one overrides the YAML. Recalibrate with a measured
straight leg and counted turns, then edit the YAML or pass the arguments; no rebuild is needed
with a symlink install, a copy install needs one for the YAML.

## Recalibrating the odometry (`scripts/odom_calibrate.py`)

Read-only, plain rclpy (no console): subscribes to `/<ns>/odometry/wheels` and `/<ns>/robot_status`, writes a jsonl; `analyze` gives linear and angular scale factors.
```bash
source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=0 RMW_IMPLEMENTATION=rmw_fastrtps_cpp   # match the driver
S=src/roverrobotics_ros2/roverrobotics_driver/scripts/odom_calibrate.py
python3 $S record --out run.jsonl --duration 300
python3 $S analyze run.jsonl --forward-m 2.362 --right-turns 5 --left-turns 5
```
`ros2 run roverrobotics_driver odom_calibrate ...` is the same after a build is sourced. The jsonl is a `meta` line, then `{t, odom{x,y,yaw,vx,wz,stamp}, rpm[4]}` samples and `{t, marker}` lines. `analyze` imports no ROS.
Optional: `record --progress` prints a `{"progress": {"t", "samples"}}` line each second; `analyze --current-linear-scale S --current-traction T` (the values the driver logged at start) adds `suggested` (`s' = s*L`, `t' = t*A/L`; L the linear scale, A the combined turn scale); an empty `--namespace` means root topics.
Test: `test/test_odom_calibrate.py` (plain pytest).

## Appendix: `pro_config.yaml`, before and after `69e9303`

The driver's own default names are absolute (`/cmd_vel`, ...), which would ignore a
namespace, so every one the lab uses is set in the file as a relative name.

| Parameter | Before | After |
|---|---|---|
| node key | `roverrobotics_driver` (matches the root namespace only) | `/**/roverrobotics_driver` (matches any namespace; `joys_manager.py` subscribes to relative `joy` for the same reason) |
| `speed_topic` | `/cmd_vel` | `cmd_vel` |
| `odom_topic` | `/odometry/wheels` | `odometry/wheels` |
| `robot_status_topic`, `robot_info_topic`, `robot_info_request_topic` | commented out (absolute default) | `robot_status`, `robot_info`, `robot_info/request` |
| `estop_trigger_topic`, `estop_reset_topic`, `trim_topic` | commented out (absolute default) | `soft_estop/trigger`, `soft_estop/reset`, `trim_event` |
| `publish_tf` | `false` | `true` (`3f4a0c4`) |

Also in `pro_config.yaml`, unchanged: `device_port: "/dev/rover-pro"`, `control_mode: "OPEN_LOOP"`,
and the `joy_manager` block (throttle steps, speed limits) that `pro_teleop.launch.py` reads.
