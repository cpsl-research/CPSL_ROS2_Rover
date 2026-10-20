# 2. Namespace and tf

Run the driver under a ROS namespace so several robots can share one network, and see where
the robot's `tf` goes. The lab added this to the upstream driver.
Start from [First drive](01_first_drive.md).

## Set a namespace

`pro.launch.py`, `pro_teleop.launch.py` and `ps4_controller.launch.py` all take `namespace`.
The default is empty, which is the root namespace: the same topic names as upstream.

```bash
ros2 launch roverrobotics_driver pro_teleop.launch.py namespace:=cpsl_ugv_1
ros2 launch roverrobotics_driver pro_teleop.launch.py --show-args    # lists joy_dev, namespace
```

`pro_teleop.launch.py` passes the value to the other two. Run `pro.launch.py` alone if you
want the driver without the gamepad.

## What moves

Every node and topic sits under the namespace, because the launch files use
`PushRosNamespace` and every topic name in `config/pro_config.yaml` and
`config/topics.yaml` is relative (no leading `/`). In `ros2 node list` and `ros2 topic list`
you should see:

| Name | Notes |
|---|---|
| `/cpsl_ugv_1/roverrobotics_driver` | the driver (it exits and restarts every second if no robot answers) |
| `/cpsl_ugv_1/robot_state_publisher`, `joint_state_publisher`, `joy_manager`, `joy_node` | |
| `/cpsl_ugv_1/cmd_vel` | what the driver listens to (`speed_topic`) |
| `/cpsl_ugv_1/odometry/wheels`, `robot_status`, `soft_estop/trigger`, `soft_estop/reset` | driver topics |
| `/cpsl_ugv_1/joy`, `joint_states`, `robot_description` | |
| `/cpsl_ugv_1/tf`, `/cpsl_ugv_1/tf_static` | see below |

Send a command to a namespaced robot with
`ros2 topic pub -r 5 /cpsl_ugv_1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"`, and stop
it with Ctrl-C and a zero command. To use another tool with this robot, remap its `cmd_vel`
to `/cpsl_ugv_1/cmd_vel`.

## tf goes to `<namespace>/tf`

`pro.launch.py` remaps `/tf` to `tf` and `/tf_static` to `tf_static` for everything it
starts, so each robot publishes its own `tf` tree and never the global `/tf`. At the root
namespace the remap changes nothing.

- The driver publishes the transform `odom` to `base_link` (`odom_frame_id` and
  `odom_child_frame_id` in `pro_config.yaml`) when `publish_tf: true`, which the lab set
  as the default. Its log says `Publishing Robot TF on odometry/wheels`.
- `robot_state_publisher` publishes the URDF's fixed links on `<namespace>/tf_static`.
- **Frame names are not prefixed.** Two robots both have `odom` and `base_link`. Keep each
  tree on its own `tf` topic, and give any tool that reads it the same remap
  (`--ros-args -r /tf:=/cpsl_ugv_1/tf -r /tf_static:=/cpsl_ugv_1/tf_static`).
- **Set `publish_tf: false`** if you add a filter (for example `robot_localization`) that
  publishes `odom` to `base_link` itself. Two publishers of one transform fight.

To watch the transforms: `ros2 topic echo /cpsl_ugv_1/tf`.

## Two robots on one computer

Give each launch its own `namespace`. `pro.launch.py` loads one fixed `pro_config.yaml`,
so both would open the same `device_port`. A second robot on the same computer needs its
own copy of that config and launch file; this fork does not provide one. The namespace
keeps topics and tf apart when each robot has its own computer on a shared network.
