# Developing CPSL_ROS2_Rover

For someone changing this fork. To install and drive, start at the [first tutorial](tutorials/01_first_drive.md).

## Layout

```
scripts/deps/rover.sh            apt dependencies (+ _common.sh, the shared helpers)
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
| `launch/accessories.launch.py` | the `bno055` remap made relative (`imu` to `imu/data`) | `69e9303` |
| `../roverrobotics_input_manager/scripts/joys_manager.py` | subscribes to `joy`, not `/joy` | `69e9303` |
| `config/ps4_controller_config.yaml` | right stick rotates, not the left trigger; several axis indices changed (each marked in the file) | `f86b620` |

The idea is "no absolute names anywhere", so a namespace moves everything. Give any new topic a relative name.

Later lab commits only delete files (the `bno055`, `rplidar_ros` and Gazebo packages) or add
`scripts/deps/`, `TODO.md` and these docs. `accessories.launch.py` and `config/accessories.yaml`
were not edited, so enabling an accessory fails at launch (see the README).

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

There are no tests for the lab's changes. These run on any machine with ROS installed:

```bash
for f in scripts/deps/*.sh; do bash -n "$f"; done
colcon build && source install/setup.bash
ros2 launch roverrobotics_driver pro_teleop.launch.py --show-args
ros2 launch roverrobotics_driver pro_teleop.launch.py namespace:=test   # then, in a second terminal:
ros2 node list; ros2 topic list     # expect /test/... names
```

With no robot the driver logs a fatal "Did not receive any data" and is restarted every
second; the other nodes still start. That is enough to check names and `tf` remaps. If a
robot is plugged in at `/dev/rover-pro`, the launch opens it, so unplug it or stop other
programs using the port first.

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
