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

**Accessories are not supported:** leave every `active` flag in `config/accessories.yaml` `false`.

## Quick start

Full steps, with the udev rule and the PS4 pad, are in [First drive](docs/tutorials/01_first_drive.md).

```bash
git clone https://github.com/cpsl-research/CPSL_ROS2_Rover.git && cd CPSL_ROS2_Rover
sudo bash scripts/deps/rover.sh                 # apt dependencies (ROS Jazzy already installed)
source /opt/ros/jazzy/setup.bash
colcon build                                    # plain build, not --symlink-install
source install/setup.bash
ros2 launch roverrobotics_driver pro_teleop.launch.py
```

The Pro must appear as `/dev/rover-pro`, a name made by a udev rule that this repo does not
install; the tutorial gives the rule and the command.

## Tutorials

1. [First drive](docs/tutorials/01_first_drive.md): dependencies, build, drive with a PS4 pad.
2. [Namespace and tf](docs/tutorials/02_namespace_and_tf.md): run one or more robots under a name; where `tf` goes.

## Other docs

- [`docs/DEVELOPING.md`](docs/DEVELOPING.md): for developers: the lab's changes and rebasing on upstream.
- [`TODO.md`](TODO.md): known issues, written to paste into an issue.
- The lab GUI [console](https://github.com/cpsl-research/console) can build and run this repo; nothing here needs it.
