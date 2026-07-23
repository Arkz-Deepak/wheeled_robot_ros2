#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
import math
from rclpy.qos import qos_profile_sensor_data

class SimpleNavigator(Node):
    def __init__(self):
        super().__init__('simple_navigator')
        
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, qos_profile_sensor_data)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_profile_sensor_data)
        self.goal_sub = self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        
        # State Machine
        self.state = 'WAITING_FOR_GOAL'
        self.current_pos = [0.0, 0.0]
        self.yaw = 0.0
        self.goal_pos = None
        
        # Smart Obstacle Distances
        # Smart Obstacle Distances
        self.front_distance = 10.0
        self.left_distance = 10.0
        self.right_distance = 10.0
        
        # INCREASED: Give the robot a larger buffer for angled obstacles
        self.safe_dist = 0.55
        
        # Timer variables
        self.state_start_time = 0.0
        self.delay_duration = 3.0 
        self.clearance_time = 2.5 # How many seconds to drive straight to bypass the object
        
        self.timer = self.create_timer(0.1, self.control_loop)

    def odom_callback(self, msg):
        self.current_pos[0] = msg.pose.pose.position.x
        self.current_pos[1] = msg.pose.pose.position.y
            
        q = msg.pose.pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.yaw = math.atan2(siny_cosp, cosy_cosp)

    def scan_callback(self, msg):
        ranges = msg.ranges
        clean_ranges = [r if not math.isinf(r) else 10.0 for r in ranges]
        
        # Widen the front cone to 80 degrees to catch thin table legs
        self.right_distance = min(clean_ranges[90:140]) if len(clean_ranges[90:140]) > 0 else 10.0
        self.front_distance = min(clean_ranges[140:220]) if len(clean_ranges[140:220]) > 0 else 10.0
        self.left_distance = min(clean_ranges[220:270]) if len(clean_ranges[220:270]) > 0 else 10.0

    def control_loop(self):
        msg = Twist()
        current_time = self.get_clock().now().nanoseconds / 1e9 

        if self.state == 'WAITING_FOR_GOAL':
            return 
            
        elif self.state == 'START_DELAY':
            if (current_time - self.state_start_time) >= self.delay_duration:
                self.state = 'MOVE_TO_GOAL'
                self.get_logger().info('==== STARTING JOURNEY ====')
            return

        elif self.state == 'GOAL_REACHED_DELAY':
            if (current_time - self.state_start_time) >= self.delay_duration:
                self.state = 'WAITING_FOR_GOAL'
                self.goal_pos = None 
                self.get_logger().info('==== READY FOR NEW GOAL ====')
            return

        # Distance calculation
        dist_to_goal = math.sqrt((self.goal_pos[0] - self.current_pos[0])**2 + (self.goal_pos[1] - self.current_pos[1])**2)

        # Stop condition
        if dist_to_goal < 0.4:
            self.get_logger().info('==== GOAL REACHED! BRAKING! ====')
            msg.linear.x = 0.0
            msg.angular.z = 0.0
            self.cmd_pub.publish(msg)
            self.state = 'GOAL_REACHED_DELAY'
            self.state_start_time = current_time
            return

        # OVERRIDE: If we get too close to something on ANY side, turn!
        # We allow the sides to get slightly closer (safe_dist - 0.15) so it can squeeze through gaps
        if (self.front_distance < self.safe_dist or 
            self.left_distance < (self.safe_dist - 0.15) or 
            self.right_distance < (self.safe_dist - 0.15)) and self.state != 'AVOID_OBSTACLE_TURN':
            
            self.state = 'AVOID_OBSTACLE_TURN'
            self.get_logger().warn(f'OBSTACLE TOO CLOSE! F:{self.front_distance:.2f} L:{self.left_distance:.2f} R:{self.right_distance:.2f}. Evading!')
            
        ## STATE 1: Turning away from the obstacle
        if self.state == 'AVOID_OBSTACLE_TURN':
            # FIX: Wait until the front AND the sides are clear before driving forward!
            if (self.front_distance > (self.safe_dist + 0.1) and 
                self.left_distance > (self.safe_dist - 0.05) and 
                self.right_distance > (self.safe_dist - 0.05)): 
                
                self.state = 'CLEARING_OBSTACLE'
                self.state_start_time = current_time
                self.get_logger().info('Path fully clear! Driving forward to bypass obstacle...')
            else:
                msg.linear.x = 0.05 
                if self.left_distance > self.right_distance:
                    msg.angular.z = 0.8 
                else:
                    msg.angular.z = -0.8
                    
        # STATE 2: Driving forward to get completely past the obstacle
        elif self.state == 'CLEARING_OBSTACLE':
            # Drive straight for 2.5 seconds
            if (current_time - self.state_start_time) >= self.clearance_time:
                self.state = 'MOVE_TO_GOAL'
                self.get_logger().info('Bypass complete! Orienting back to goal.')
            else:
                msg.linear.x = 0.15
                msg.angular.z = 0.0
                time_left = self.clearance_time - (current_time - self.state_start_time)
                self.get_logger().info(f'Clearing obstacle... (Time left: {time_left:.1f}s)', throttle_duration_sec=0.5)

        # STATE 3: Standard Movement toward the goal
        elif self.state == 'MOVE_TO_GOAL':
            angle_to_goal = math.atan2(self.goal_pos[1] - self.current_pos[1], self.goal_pos[0] - self.current_pos[0])
            angle_error = angle_to_goal - self.yaw
            angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))
            
            # This log will update every 1 second while driving normally
            self.get_logger().info(f'[MOVE] Dist to goal: {dist_to_goal:.2f}m | Angle Err: {math.degrees(angle_error):.1f}°', throttle_duration_sec=1.0)

            if abs(angle_error) > 0.3:
                msg.linear.x = 0.05 
                msg.angular.z = max(min(1.0 * angle_error, 0.5), -0.5)
            else:
                msg.linear.x = 0.15 
                msg.angular.z = 0.0
                
        self.cmd_pub.publish(msg)

    def goal_callback(self, msg):
        if self.state == 'WAITING_FOR_GOAL' or self.state == 'GOAL_REACHED_DELAY':
            self.goal_pos = [msg.pose.position.x, msg.pose.position.y]
            self.state = 'START_DELAY'
            self.state_start_time = self.get_clock().now().nanoseconds / 1e9
            self.get_logger().info(f'==== NEW GOAL ==== X={self.goal_pos[0]:.2f}, Y={self.goal_pos[1]:.2f}. Waiting {self.delay_duration}s...')
        else:
            self.get_logger().warn('Busy! Ignoring goal.')

def main(args=None):
    rclpy.init(args=args)
    node = SimpleNavigator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()