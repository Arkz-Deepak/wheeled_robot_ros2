cmake_minimum_required(VERSION 3.8)
project(wheeled_robot VERSION 0.0.1 LANGUAGES CXX)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# Export runtime dependencies so other packages can find them if needed
ament_export_dependencies(launch launch_ros robot_state_publisher joint_state_publisher_gui rviz2 ros_gz_sim ros_gz_bridge)

# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(DIRECTORY 
  rviz
  launch
  urdf
  config
  map
  worlds
  DESTINATION share/${PROJECT_NAME}
)

# Install Python nodes
install(PROGRAMS
  nodes/obstacle_avoidance.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
