from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace, SetRemap
from launch_ros.parameter_descriptions import ParameterValue


# Optional odometry overrides: launch argument -> driver parameter. An empty
# argument leaves the value from pro_config.yaml in force.
ODOM_ARGS = {
    'odom_linear_scale': 'wheel odometry speed scale (YAML default if empty)',
    'odom_traction_factor': 'wheel odometry angular traction factor (YAML default if empty)',
    'odom_wheel_separation': 'wheel odometry wheel separation in m (YAML default if empty)',
}


def _driver_node(context, hardware_config):
    overrides = {}
    for name in ODOM_ARGS:
        text = LaunchConfiguration(name).perform(context).strip()
        if text:
            try:
                overrides[name] = float(text)
            except ValueError:
                raise RuntimeError(
                    f"launch argument {name}:={text!r} is not a number")
    return [Node(
        package = 'roverrobotics_driver',
        name = 'roverrobotics_driver',
        executable = 'roverrobotics_driver',
        # later entries win, so overrides apply after pro_config.yaml
        parameters = [hardware_config] + ([overrides] if overrides else []),
        output='screen',
        respawn=True,
        respawn_delay=1
    )]


def generate_launch_description():
    rover_path = get_package_share_path('roverrobotics_description')
    default_model_path = rover_path / 'urdf/rover_4wd.urdf'
    
    model_arg = DeclareLaunchArgument(name='model', default_value=str(default_model_path),
                                      description='Absolute path to robot urdf file')
    robot_description = ParameterValue(Command(['xacro ', LaunchConfiguration('model')]),
                                       value_type=str)
   
    hardware_config = Path(get_package_share_directory(
        'roverrobotics_driver'), 'config', 'pro_config.yaml')
    assert hardware_config.is_file()

    # ROS namespace for everything this launch starts. Empty (the default) is
    # the root namespace, i.e. the driver's behaviour before this argument
    # existed. pro_config.yaml names its topics relatively, so they follow it.
    namespace_arg = DeclareLaunchArgument(
        name='namespace', default_value='',
        description='ROS namespace for the driver, tf and accessories (empty = root)')

    ld = LaunchDescription()

    robot_driver = OpaqueFunction(function=_driver_node, args=[hardware_config])

    accessories_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([get_package_share_directory('roverrobotics_driver'), '/launch/accessories.launch.py']),
    )
   
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher'
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )
    
    # tf goes to <ns>/tf and <ns>/tf_static, never the global /tf. The remaps
    # are a no-op at the root namespace. robot_state_publisher and
    # joint_state_publisher sit in the group, so /robot_description and
    # /joint_states are per robot too.
    group = GroupAction([
        PushRosNamespace(LaunchConfiguration('namespace')),
        SetRemap(src='/tf', dst='tf'),
        SetRemap(src='/tf_static', dst='tf_static'),
        robot_driver,
        accessories_launch,
        joint_state_publisher_node,
        robot_state_publisher_node,
    ])

    ld.add_action(model_arg)
    ld.add_action(namespace_arg)
    for arg_name, arg_doc in ODOM_ARGS.items():
        ld.add_action(DeclareLaunchArgument(arg_name, default_value='', description=arg_doc))
    ld.add_action(group)
   
    return ld
