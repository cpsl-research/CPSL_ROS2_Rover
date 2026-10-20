# CPSL_ROS2_Rover

The CPSL's fork of Rover Robotics' ROS 2 driver for the **Rover Pro**, a four-wheel-drive
mobile base. It adds a launch-time namespace, per-robot `tf`, and PS4 teleop over SSH.
Targets Ubuntu 24.04 and ROS 2 [Jazzy](https://docs.ros.org/en/jazzy/Installation.html).

**Only the Pro is supported.** The upstream packages still contain launch files and
configs for other models (Max, Mega, Mini, Miti, Zero); the lab does not use or test them.

## What is here

| Package (`src/roverrobotics_ros2/`) | What it does |
|---|---|
| `roverrobotics_driver` | C++ driver node for the serial link, plus the launch files and configs |
| `roverrobotics_description` | URDF and meshes (`rover_4wd.urdf`) |
| `roverrobotics_input_manager` | `joys_manager.py`: gamepad `joy` messages to `cmd_vel` |

Upstream: [RoverRobotics/roverrobotics_ros2](https://github.com/RoverRobotics/roverrobotics_ros2).

**Accessories are not supported in this fork.** `roverrobotics_driver/launch/accessories.launch.py`
still reads `config/accessories.yaml` and would start `rplidar_ros` or `bno055` if
their `active` flag were set to `true`. Those packages are no longer here, so leave
them `false` (the default).

## Quick start

```bash
sudo bash scripts/deps/rover.sh                 # apt dependencies (ROS Jazzy already installed)
colcon build                                    # from the repo root
source install/setup.bash
ros2 launch roverrobotics_driver pro_teleop.launch.py
```

Use plain `colcon build`, not `--symlink-install`; see the first tutorial.
The Pro must be connected at `/dev/rover-pro`. That device name comes from a udev rule
that this repo does not install. Rover Robotics' install scripts do:
[`rover_install_scripts_ros2`](https://github.com/RoverRobotics/rover_install_scripts_ros2).

## Tutorials

1. [First drive](docs/tutorials/01_first_drive.md): dependencies, build, drive with a PS4 pad.
2. [Namespace and tf](docs/tutorials/02_namespace_and_tf.md): run one or more robots under a name; where `tf` goes.

## Other docs

- [`docs/DEVELOPING.md`](docs/DEVELOPING.md): the lab's changes, rebasing on upstream, install types.
- [`TODO.md`](TODO.md): known issues, written to paste into an issue.
- The lab GUI [console](https://github.com/cpsl-research/console) can build and run this repo; nothing here needs it.
