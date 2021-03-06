#!/usr/bin/env python
from __future__ import division

import rospy
import math
import time
import numpy as np

from rosrider_lib.rosrider import ROSRider

from std_msgs.msg import String


class LineFollower:

    def __init__(self):

        self.robot = ROSRider('robot1', 500.0)
        self.lateralKp = 5.2
        self.lateralKd = 10.0
        self.multiplier = 0.9
        self.max_linear = 1.1
        self.sensor_row = []
        self.weights = [0.18, 0.169, 0.1575, 0.146, 0.135, 0.124, 0.112, 0.101, 0.09, 0.0788, 0.0675, 0.0562, 0.045, 0.03375, 0.0225, 0.01125, 
                        -0.01125, -0.0225, -0.03375, -0.045, -0.0562, -0.0675, -0.0788, -0.09, -0.101, -0.112, -0.124, -0.135, -0.146, -0.1575, -0.169, -0.18] 
        self.last_dev_index = 0
        self.started = False
        rospy.wait_for_message('/simulation_metrics', String)

        # grace period, do not remove
        time.sleep(0.5)
        self.started = True

    def main(self):
        prev_lateral_error = 0

        while self.robot.is_ok():
            # if robot is shutting down, or not yet started, do not process image
            if self.robot.is_shutdown or not self.started:
                print('Robot shutdown!')
                return
            # reinitialize the array each time, new image arrives
            self.sensor_row = []

            image = self.robot.get_image()
            for i in range(image.width):
                brightness = (0.2126 * ord(image.data[i * 3])) + (0.7152 * ord(image.data[i * 3 + 1])) + (0.0722 * ord(image.data[i * 3 + 2]))
                self.sensor_row.append(brightness)

            max_value_index = self.sensor_row.index(max(self.sensor_row)) # 0-31 !
            dev_pixel = 15 - max_value_index

            num = 0
            den = 0
            # Interpolation
            mult = np.multiply(self.weights, self.sensor_row)
            for i in range(len(mult)):
                num += mult[i]
                den += self.sensor_row[i]
            dev_error = num/den

            angle_remaining = math.atan2(dev_error, 0.38) # Radians!

            # Calculate angular velocity
            lateral_error = angle_remaining
            lateral_diff = lateral_error - prev_lateral_error
            prev_lateral_error = lateral_error
            angular = (self.lateralKp * lateral_error) + (self.lateralKd * lateral_diff)

            # Linear velocity
            max_dev = 0.09
            g = 9.81
            I = 0.01
            if angle_remaining < 0.0001:
                angle_remaining = math.pow(self.max_linear, 2) * 2 * math.acos(1-max_dev*g*I)
            linear = self.multiplier * math.sqrt(max_dev * g * I / (1 - math.cos(angle_remaining / 2)))
            linear = min(linear, self.max_linear)

            # Control commands
            self.robot.move(linear)
            self.robot.rotate(angular)

        self.robot.stop()


if __name__ == '__main__':
    try:
        node = LineFollower()
        node.main()
    except rospy.ROSInterruptException:
        pass

