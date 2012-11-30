#!/usr/bin/python
#***************************************************************
#
# Copyright (c) 2010
#
# Fraunhofer Institute for Manufacturing Engineering	
# and Automation (IPA)
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#
# Project name: 
# ROS stack name: cob_driver
# ROS package name: cob_odroidx_interface
#								
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#			
# Author: Joshua Hampp
#
# Date of creation: June 2010
# ToDo:
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Fraunhofer Institute for Manufacturing 
#       Engineering and Automation (IPA) nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License LGPL as 
# published by the Free Software Foundation, either version 3 of the 
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License LGPL for more details.
# 
# You should have received a copy of the GNU Lesser General Public 
# License LGPL along with this program. 
# If not, see <http://www.gnu.org/licenses/>.
#
#****************************************************************

import roslib; 
roslib.load_manifest('ipa_odroidx_interface')
import rospy

from sensor_msgs.msg import ChannelFloat32

from spi import SPIDev, spi_transfer
import struct


class AVRInterface:
	SET_OUTPUT	=0x10
	SET_MOTOR	=0x20
	GET_ANALOG	=0x30
	GET_INPUT	=0x40
	SETUP		=0x50

	def __init__(self, dev='/dev/spidev0.0'):
		#setup device
		self.spi = SPIDev(dev)

	def write(self,cmd, data=[], expect=0):
		valtransfer, _, rbuf = spi_transfer(cmd+data, expect=1)
		# actually do the transfer
		s.do_transfers([cmdtransfer, valtransfer])
		return rbuf.raw

	def setup(self):
		assert self.write(SETUP,[],1)=='O'

	def set_output(self, o):
		out = 0
		for i in range(0,6):
			out += (o[i]<<i)
		out = chr( out )
		self.write(SET_OUTPUT,[out])

	def set_motor(self, motor, back, speed):
		self.write( chr(SET_MOTOR|motor|(back<<1)), [chr(speed)])

	def get_analog(self, ch):
		assert(ch<4 and ch>=0)
		data = self.write( chr(GET_ANALOG|ch), [], 2)
		return ord(data[0])*255 + ord(data[1])

	def get_input(self):
		data = self.write( GET_INPUT, [], 1)
		r=[]
		for i in range(0,4):
			r.append( ord(data)&(1<<i) )
		return r

class AVRControl:
	def __init__(self):
		self.ns_global_prefix = "/light_controller"
		self.pub_marker = rospy.Publisher("state", ChannelFloat32)
		rospy.Subscriber("command", ChannelFloat32, self.setCallback)

		if not rospy.has_param(self.ns_global_prefix + "/polling_interval"):
			self.polling_interval = 1
		else:
			self.polling_interval = rospy.get_param(self.ns_global_prefix + "/polling_interval")

		if not rospy.has_param(self.ns_global_prefix + "/analog_channels"):
			self.analog_ch = []
		else:
			self.analog_ch = map(int, rospy.get_param(self.ns_global_prefix + "/dev").split(","))

		if not rospy.has_param(self.ns_global_prefix + "/dev"):
			self.intf = AVRInterface()
		else:
			self.intf = AVRInterface( rospy.get_param(self.ns_global_prefix + "/dev") )

	def setCallback(self, data):
		assert(len(data.values)==8)
		for i in range(0,2):
			self.intf.set_motor(i, data.values[i]<0, data.values[i]*255)
		o=[]
		for i in range(2,8):
			o.append( data.values[i]>0.5 )
		self.intf.set_output(o)

	def publish(self):
		data = map(float, self.intf.get_input() )
		for a in self.analog_ch:
			data[a] = self.intf.get_analog(a)/float(0x400)
		
		ch = ChannelFloat32()
		ch.name = "avr_measurements"
		ch.values = data
		self.pub_marker.publish(ch)
			

if __name__ == '__main__':
	rospy.init_node('odroidx_interface')
	ac = AVRControl()

	r = rospy.Rate(ac.polling_interval)
	while not rospy.is_shutdown():
		ac.publish_marker()
		r.sleep()
	