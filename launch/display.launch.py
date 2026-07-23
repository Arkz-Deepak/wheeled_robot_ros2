import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    # 1. Get the path to your URDF file
    pkg_name = 'wheeled_robot'
    # Use get_package_share_directory instead of get_package_prefix!
    urdf_file = os.path.join(get_package_share_directory(pkg_name), 'urdf', 'four_wheel.urdf')

    # Read the URDF file so we can pass it as a parameter
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    # 2. Robot State Publisher: The core node that calculates the TF2 math
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        # MUST BE PLURAL: parameters
        parameters=[{'robot_description': robot_desc}]
    )

    # 3. Joint State Publisher GUI: Gives you a pop-up with sliders to spin your wheels
    jsp_gui_node = Node(
        package='joint_state_publisher_gui',
        # MUST BE SPELLED CORRECTLY: executable
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui'
    )

    # 4. RViz2: The 3D Visualizer
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen'
    )

    # Launch them all!
    return LaunchDescription([
        rsp_node,
        jsp_gui_node,
        rviz_node
    ])