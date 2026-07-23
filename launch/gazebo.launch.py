import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription

def generate_launch_description():

    # 1. Get the path to your URDF file
    pkg_name = 'wheeled_robot'
    # Use get_package_share_directory instead of get_package_prefix!
    urdf_file = os.path.join(get_package_share_directory(pkg_name), 'urdf', 'four_wheel.urdf')
    gazebo_launch_path = os.path.join(get_package_share_directory('ros_gz_sim'),'launch','gz_sim.launch.py')

    # Read the URDF file so we can pass it as a parameter
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    world_file_path = os.path.join(get_package_share_directory(pkg_name),'worlds','world.sdf')
    bridge_params = os.path.join(get_package_share_directory(pkg_name),'config','ros_gz_bridge.yaml')
    # Force Gazebo to load the TB3 pillar world
    #world_file_path = '/opt/ros/jazzy/share/turtlebot3_gazebo/worlds/turtlebot3_world.world'
    # 2. Robot State Publisher: The core node that calculates the TF2 math
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        # MUST BE PLURAL: parameters
        parameters=[
            {'robot_description': robot_desc,
            'use_sim_time': True}]
    )
    gazebo_world_boot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gazebo_launch_path),
        launch_arguments=[('gz_args',f'-r {world_file_path}')]#{world_file_path}
    )
    spawn_node = Node(
        package='ros_gz_sim',
        executable='create',
        # Changed '-file' to '-topic' and 'urdf_file' to 'robot_description'
        arguments=['-topic', 'robot_description', '-name', 'four_wheel', '-z', '5.5', '-x', '-2.0', '-y', '-0.5']
    )
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '--ros-args',
            '-p', f'config_file:={bridge_params}',
        ],
        output='screen'
    )

    nav_node = Node(
        package=pkg_name,
        executable='obstacle_avoidance.py',
        output='screen'
    )
    return LaunchDescription([
        rsp_node,
        gazebo_world_boot,
        spawn_node,
        bridge_node,
        nav_node
    ])
