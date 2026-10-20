#!/usr/bin/env bash
# Rover Pro driver: what roverrobotics_driver, roverrobotics_description and
# roverrobotics_input_manager need to build and run.
#
# Used by console, which runs it inside its own container before building
# those three packages out of tree. On a host, run it with `sudo bash`.
#
# Listed rather than resolved with rosdep because the package.xmls are wrong in
# both directions: roverrobotics_description declares rviz2, a desktop GUI, and
# nothing declares joy_linux, which ps4_controller.launch.py runs.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

ROS_DISTRO="${ROS_DISTRO:-jazzy}"

apt_ensure \
    libeigen3-dev \
    "ros-${ROS_DISTRO}-diagnostic-updater" \
    "ros-${ROS_DISTRO}-tf2-geometry-msgs" \
    "ros-${ROS_DISTRO}-xacro" \
    "ros-${ROS_DISTRO}-robot-state-publisher" \
    "ros-${ROS_DISTRO}-joint-state-publisher" \
    "ros-${ROS_DISTRO}-joy" \
    "ros-${ROS_DISTRO}-joy-linux"
