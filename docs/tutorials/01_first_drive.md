# 1. First drive

Install the dependencies, build the workspace, and drive a Rover Pro with a PS4 gamepad.
No other repo is needed.

**You need:** a Rover Pro connected to this computer by USB serial, a PS4 pad, Ubuntu 24.04
with ROS 2 Jazzy ([install guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)),
and `colcon` (`sudo apt install python3-colcon-common-extensions`). Put the robot where
it can move safely, or on blocks, before the first drive.

## 1. Make `/dev/rover-pro` exist

`device_port` in `config/pro_config.yaml` is `/dev/rover-pro`. This repo does not install
the udev rule that creates it; Rover Robotics' scripts do. Run `setup_rover.sh` from
[`rover_install_scripts_ros2`](https://github.com/RoverRobotics/rover_install_scripts_ros2)
(see its README), then replug the robot and check:

```bash
ls -l /dev/rover-pro      # a symlink to /dev/ttyUSB0 or similar
```

If your robot enumerates under another name, change `device_port` in `pro_config.yaml`.

## 2. Install dependencies

```bash
git clone https://github.com/cpsl-research/CPSL_ROS2_Rover.git
cd CPSL_ROS2_Rover
sudo bash scripts/deps/rover.sh
```

`scripts/deps/rover.sh` installs, with apt: `libeigen3-dev` and the Jazzy packages
`diagnostic-updater`, `tf2-geometry-msgs`, `xacro`, `robot-state-publisher`,
`joint-state-publisher`, `joy` and `joy-linux`. It must run as root, and does nothing for
packages already installed. It lists them instead of using `rosdep` because the
`package.xml` files are wrong (the description package asks for `rviz2`; nothing asks for `joy_linux`).

## 3. Build

```bash
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

Use a plain build. With `--symlink-install`, `joys_manager.py` is installed as a link to a
file that is not executable, and the next step stops with
`executable 'joys_manager.py' not found` (see `TODO.md`, first item).

You should see `Summary: 3 packages finished` (the driver prints compiler warnings).

## 4. Drive

Connect the pad (by USB, or pair it over Bluetooth) and check that it appears:

```bash
ls /dev/input/js*         # normally /dev/input/js0
ros2 launch roverrobotics_driver pro_teleop.launch.py
```

`pro_teleop.launch.py` starts `pro.launch.py` (driver, `robot_state_publisher`,
`joint_state_publisher`) and `ps4_controller.launch.py` (`joy_linux_node` plus `joys_manager.py`).
Over SSH, or when the pad is `js1`, name it: `joy_dev:=/dev/input/js1`. The lab added
that argument so the nodes start from an SSH session.

In the launch output you should see the driver log `Connecting to robot at /dev/rover-pro` and
`Receiving velocity command from cmd_vel`.

| Control | Effect (`ps4_controller_config.yaml`, `topics.yaml`) |
|---|---|
| Left stick, up/down | Forward / back |
| Right stick, left/right | Turn (the lab changed the axis numbers so this works) |
| D-pad up/down | Change the linear throttle (a multiplier on the stick) by 0.22 per press |
| D-pad left/right | Change the angular throttle the same way |

The throttles start at 0.66 (linear) and 1.1 (angular), and output is clamped to 1.10 m/s
and 4.84 rad/s. All of these are in the `joy_manager` block of `pro_config.yaml`.

## 5. Check from a second terminal

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list           # includes /cmd_vel, /joy, /odometry/wheels, /robot_status, /tf
ros2 topic echo /cmd_vel  # move a stick
```

## If it does not work

| Message | Meaning |
|---|---|
| `Did not receive any data from the robot or the data is stale` (driver, fatal; it restarts every second) | Nothing answered on `/dev/rover-pro`: wrong device, no permission, robot off, or another program holds the port |
| `Couldn't open joystick /dev/input/js0` | The pad is not connected, or is under another name: use `joy_dev:=` |
| `IndexError when updating controller states` (`joys_manager`) | The device is not a PS4 pad; the axis numbers do not match |

Next: [namespace and tf](02_namespace_and_tf.md).
