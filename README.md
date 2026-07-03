# 🚀 Rover Robotics Workspace

This repository is a consolidated workspace containing a collection of ROS 2 packages that were originally maintained in separate Git repositories. They are now tracked directly in this single repository for easier development, compilation, and integration.

---

## 📦 Contained Packages

### 1. [bno055](file:///home/rover/rover_workspace/src/bno055)
* **Description:** Bosch BNO055 IMU driver for ROS 2.
* **Details:** Connects to the BNO055 sensor over serial UART or I2C and publishes standard ROS 2 IMU messages.

### 2. [roverrobotics_ros2](file:///home/rover/rover_workspace/src/roverrobotics_ros2)
* **Description:** Core ROS 2 packages for Rover Robotics mobile platforms (e.g., Rover Zero, Mitus, Pro).
* **Included Sub-packages:**
  * `roverrobotics_driver`: The hardware driver wrapper that handles communication with the robot controller.
    * 🔧 *Modifications:* Edited [ps4_controller_config.yaml](file:///home/rover/rover_workspace/src/roverrobotics_ros2/roverrobotics_driver/config/ps4_controller_config.yaml) to configure accurate rotation values.
  * `roverrobotics_description`: URDF models, meshes, and robot state configurations.
  * `roverrobotics_gazebo`: Launch and world files for Gazebo simulation.
  * `roverrobotics_input_manager`: Teleoperation nodes mapping joystick inputs to robot movements.
* **🔧 Key Improvements:**
  * **Accurate PS4 Rotation:** Fixed controller input values inside [ps4_controller_config.yaml](file:///home/rover/rover_workspace/src/roverrobotics_ros2/roverrobotics_driver/config/ps4_controller_config.yaml) to allow the right joystick to control rotation instead of the left trigger.
  * **SSH Teleop Support (`joy_dev` parameter):** The [ps4_controller.launch.py](file:///home/rover/rover_workspace/src/roverrobotics_ros2/roverrobotics_driver/launch/ps4_controller.launch.py) file has been modified to declare and receive a `joy_dev` launch parameter (default: `/dev/input/js0`). This ensures that joystick nodes launch correctly without path errors even when started via an SSH terminal session.


### 3. [rplidar_ros](file:///home/rover/rover_workspace/src/rplidar_ros)
* **Description:** ROS 2 driver package for SLAMTEC RPLIDAR sensors.
* **Details:** Support for RPLIDAR A1/A2/A3/S1/S2/S3/T1 laser scanners, publishing laser scans to `/scan`.

---

## ⚙️ Installation Instructions

To set up the Rover Robotics platform with ROS 2, you can use the official Rover Robotics setup scripts.

### Prerequisite System Requirements
* **Operating System:** Ubuntu 22.04 (Jammy) or Ubuntu 24.04 (Noble)
* **ROS 2 Versions:** Humble or Jazzy
* **Hardware:** Jetson Orin Series, Intel NUC, Raspberry Pi, or compatible Linux computer

---

### Step 1 – Install ROS 2 (If not already installed)
If ROS 2 is not yet installed on your system, you can use the simple setup script provided by Rover Robotics:

```bash
# Clone the setup scripts repository
git clone https://github.com/RoverRobotics/rover_install_scripts_ros2
cd rover_install_scripts_ros2

# Make the installation script executable and run it
chmod +x ros2_installation.sh
./ros2_installation.sh
```
*The script will prompt you to select your desired ROS 2 distribution (Humble/Jazzy) and installation type (Desktop or Base).*

---

### Step 2 – Set Up Your Rover Configuration
Next, run the main rover configuration script to set up udev rules, services, and default configurations:

```bash
cd rover_install_scripts_ros2

# Make the setup script executable and run it
chmod +x setup_rover.sh
./setup_rover.sh
```
*The interactive installer will guide you through setting up configurations specific to your Rover hardware.*

---

### Step 3 – Building this Workspace
After setting up ROS 2 and configuring your hardware, build this workspace using `colcon`:

```bash
# Navigate to the workspace root directory
cd /home/rover/rover_workspace

# Install dependencies using rosdep
sudo apt update
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# Build the workspace
colcon build --symlink-install

# Source the workspace setup
source install/setup.bash
```
