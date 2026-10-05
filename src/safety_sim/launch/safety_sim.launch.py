import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('safety_sim')
    world = os.path.join(pkg, 'worlds', 'iti_workshop.sdf')
    rviz_cfg = os.path.join(pkg, 'rviz', 'safety.rviz')
    gz_launch = os.path.join(
        get_package_share_directory('ros_gz_sim'), 'launch',
        'gz_sim.launch.py')

    use_gazebo = LaunchConfiguration('use_gazebo')
    headless = LaunchConfiguration('headless')
    use_rviz = LaunchConfiguration('use_rviz')
    use_dashboard = LaunchConfiguration('use_dashboard')
    num_workers = LaunchConfiguration('num_workers')

    gz_flags = PythonExpression(
        ["'-r -s ' if '", headless, "' == 'true' else '-r '"])

    return LaunchDescription([
        DeclareLaunchArgument('use_gazebo', default_value='true'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run Gazebo server only (no GUI)'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('use_dashboard', default_value='true'),
        DeclareLaunchArgument('num_workers', default_value='4'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gz_launch),
            launch_arguments={'gz_args': [gz_flags, world]}.items(),
            condition=IfCondition(use_gazebo)),

        # Gives the 'world' frame a TF tree so RViz is happy
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='world_to_map',
             arguments=['0', '0', '0', '0', '0', '0', 'world', 'map']),

        Node(package='safety_sim', executable='safety_sim_node',
             name='safety_sim_node', output='screen',
             parameters=[{'num_workers': num_workers}]),

        Node(package='safety_sim', executable='dashboard',
             name='safety_dashboard', output='screen',
             condition=IfCondition(use_dashboard)),

        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', rviz_cfg], output='screen',
             condition=IfCondition(use_rviz)),
    ])
