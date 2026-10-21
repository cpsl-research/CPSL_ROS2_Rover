#!/usr/bin/env bash
# Rover Pro driver: what roverrobotics_driver, roverrobotics_description and
# roverrobotics_input_manager need to build and run.
#
# Used by console, which runs it inside its own container before building
# those three packages out of tree. On a host, run it with `sudo bash`.
#
# Usage:
#   sudo bash rover.sh           install whatever is missing
#   bash rover.sh --check        no root, installs nothing: exit 0 if every package
#                                below is installed, else exit 1 and list the missing
#                                ones on stderr. Works on plain ROS 2, without console.
#
# Listed rather than resolved with rosdep because the package.xmls are wrong in
# both directions: roverrobotics_description declares rviz2, a desktop GUI, and
# nothing declares joy_linux, which ps4_controller.launch.py runs.
ROS_DISTRO="${ROS_DISTRO:-jazzy}"

PACKAGES=(
    libeigen3-dev
    "ros-${ROS_DISTRO}-diagnostic-updater"
    "ros-${ROS_DISTRO}-tf2-geometry-msgs"
    "ros-${ROS_DISTRO}-xacro"
    "ros-${ROS_DISTRO}-robot-state-publisher"
    "ros-${ROS_DISTRO}-joint-state-publisher"
    "ros-${ROS_DISTRO}-joy"
    "ros-${ROS_DISTRO}-joy-linux"
)

# Handled before _common.sh, whose root check would fail for a normal user.
if [ "${1:-}" = "--check" ]; then
    missing=()
    for pkg in "${PACKAGES[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
            missing+=("$pkg")
        fi
    done
    if [ ${#missing[@]} -ne 0 ]; then
        echo "missing: ${missing[*]}" >&2
        exit 1
    fi
    exit 0
fi

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

apt_ensure "${PACKAGES[@]}"
