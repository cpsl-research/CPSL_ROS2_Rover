# 1. First drive

Install, build, and drive a Rover Pro with a PS4 gamepad. No other repo is needed.

**You need:** a Rover Pro connected to this computer by USB serial, a PS4 pad, Ubuntu 24.04
with ROS 2 Jazzy ([install guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)),
and `colcon` (`sudo apt install python3-colcon-common-extensions`). Put the robot on blocks
or clear floor first.

## 1. Make `/dev/rover-pro` exist

`device_port` in `config/pro_config.yaml` is `/dev/rover-pro`. A udev rule creates that name
from the robot's USB serial adapter; this repo does not install it. Pick one:

**A. Copy Rover Robotics' rule file** (the udev step of their `setup_rover.sh`):

```bash
git clone https://github.com/RoverRobotics/rover_install_scripts_ros2.git
sudo cp rover_install_scripts_ros2/udev/55-roverrobotics.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

That file also covers other Rover models and sensors and overwrites FTDI devices with a
similar signature. Their interactive `./setup_rover.sh` does far more (ROS 2, its own
`~/rover_workspace`, `~/.bashrc`, boot services); this fork does not need it.

**B. Write only the Pro rule.** The Pro's adapter reports the USB serial string `Rover Pro`
(vendor `0403` or `10c4`):

```bash
sudo tee /etc/udev/rules.d/55-roverrobotics.rules <<'RULE'
KERNEL=="ttyUSB[0-9]", ATTRS{idVendor}=="0403", ATTRS{serial}=="Rover Pro", MODE:="0777", SYMLINK+="rover-pro", RUN+="/bin/setserial /dev/%k low_latency"
KERNEL=="ttyUSB[0-9]", ATTRS{idVendor}=="10c4", ATTRS{serial}=="Rover Pro", MODE:="0777", SYMLINK+="rover-pro", RUN+="/bin/setserial /dev/%k low_latency"
RULE
sudo udevadm control --reload-rules && sudo udevadm trigger
```

`setserial` (optional apt package) lowers latency. Replug the robot, then check:

```bash
ls -l /dev/rover-pro      # a symlink to /dev/ttyUSB0 or similar
```

Without any rule, add yourself to `dialout` (`sudo usermod -aG dialout $USER`, then log out
and in) and set `device_port` in `pro_config.yaml` to the port, such as `/dev/ttyUSB0`.
If neither is in place the driver logs "Robot at /dev/rover-pro is not available" (table below).

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
`package.xml` files are incomplete.

## 3. Build

```bash
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

Use a plain build. With `--symlink-install`, `joys_manager.py` is installed as a link to a
file that is not executable, and the next step stops with
`executable 'joys_manager.py' not found` (`TODO.md`, first item). You should see `Summary: 3 packages finished`.

## 4. Drive

Connect the pad by USB, or pair it over Bluetooth (`bluetoothctl`: hold Share + PS on the
pad, then `scan on`, `pair`, `trust` and `connect` with its address). Check that it appears:

```bash
ls /dev/input/js*         # normally /dev/input/js0
source /opt/ros/jazzy/setup.bash && source install/setup.bash   # in every new terminal
ros2 launch roverrobotics_driver pro_teleop.launch.py
```

The pad must be connected to the computer that runs the launch (the robot's, if you are
logged in over SSH), not to your laptop. If it is not `js0`, name it: `joy_dev:=/dev/input/js1`.

In the launch output you should see the driver log `Connecting to robot at /dev/rover-pro` and
`Receiving velocity command from cmd_vel`.

| Control | Effect (`ps4_controller_config.yaml`, `topics.yaml`) |
|---|---|
| Left stick, up/down | Forward / back |
| Right stick, left/right | Turn (the lab changed the axis numbers so this works) |
| D-pad up/down | Change the linear throttle (a multiplier on the stick) by 0.22 per press |
| D-pad left/right | Change the angular throttle the same way |

Throttles start at 0.66 (linear) and 1.1 (angular); output is clamped to 1.10 m/s and
4.84 rad/s (`joy_manager` block of `pro_config.yaml`).

## 5. Check from a second terminal

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list           # includes /cmd_vel, /joy, /odometry/wheels, /tf
ros2 topic echo /cmd_vel  # move a stick
```

## If it does not work

| Message | Meaning |
|---|---|
| `Robot at /dev/rover-pro is not available ...` (driver, fatal; restarts every second) | The port could not be opened: no udev rule or no such device, or no permission (section 1) |
| `Did not receive any data from the robot or the data is stale` (driver, fatal; it restarts every second) | The port opened but the robot sent nothing: robot off, wrong device behind the name, or another program (another driver) holds the port |
| `Couldn't open joystick /dev/input/js0` | The pad is not connected, or is under another name: use `joy_dev:=` |
| `IndexError when updating controller states` (`joys_manager`) | The device is not a PS4 pad; the axis numbers do not match |
| The launch is fine but the robot does not move | There is no enable or deadman button: the sticks alone drive, and within 0.15 of centre counts as zero. Run `ros2 topic echo /cmd_vel` while pushing a stick. Always zero: the pad's axes do not match (test with `jstest /dev/input/js0` from `sudo apt install joystick`). Non-zero but no motion: the driver is not reaching the robot (first row), or check the robot's power switch and e-stop |

Next: [namespace and tf](02_namespace_and_tf.md).
