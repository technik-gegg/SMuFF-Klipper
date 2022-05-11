#---------------------------------------------------------------------------------------------
# SMuFF Klipper Module - V1.0
#---------------------------------------------------------------------------------------------
#
# Copyright (C) 2022 Technik Gegg <technik.gegg@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
#
# This version implements the following GCodes which can be accessed from 
# the Klipper console:
#
#   SMUFF_CONN          - Connect to the SMuFF via serial interface
#   SMUFF_DISC          - Disconnect from the SMuFF
#	SMUFF_CONNECTED		- Show current connection status
#   SMUFF_CUT           - Cut filament (if Filament-Cutter is configured)
#   SMUFF_WIPE          - Wipe nozzle (if Wiper is installed)
#   SMUFF_LID_OPEN      - Open lid servo
#   SMUFF_LID_CLOSE     - Close lid servo
#   SMUFF_SET_SERVO     - Position a servo
#   SMUFF_TOOL_CHANGE   - Change the current tool (mainly called from Tn GCodes)
#   SMUFF_INFO          - Query the firmware info from SMuFF
#   SMUFF_STATUS        - Query the status from SMuFF
#   SMUFF_SEND          - Send GCode to the SMuFF
#   SMUFF_PARAM         - Send configuration parameters to the SMuFF
#	SMUFF_MATERIALS		- Query the materials configured on the SMuFF
#	SMUFF_SWAPS			- Query the tool swaps configured on the SMuFF
#	SMUFF_LIDMAPPINGS	- Query the lid servo mappings configured on the SMuFF
#	SMUFF_LOAD			- Load filament on active tool on the SMuFF
#	SMUFF_UNLOAD		- Unload filament from active tool on the SMuFF
#	SMUFF_HOME			- Home Selector (and Revolver if available)
#	SMUFF_MOTORS_OFF	- Turn stepper motors on the SMuFF off
#	SMUFF_CLEAR_JAM		- Resets the Feeder Jammed flag on the SMuFF
# 	SMUFF_RESET			- Resets the SMuFF
#
# During runtime you have the option to query the following values from within
# scripts or macros:
#
#	printer.smuff.tools   			(int) 		The number of tools available on the SMuFF
#	printer.smuff.activetool		(int)		The active tool number, -1 if Selector is homed
#	printer.smuff.pendingtool		(int)		The new tool number requested by a tool change, -1 if no tool change is pending
#	printer.smuff.selector			(bool) 		True = triggered
#	printer.smuff.revolver			(bool) 		True = triggered
#	printer.smuff.feeder			(bool) 		True = triggered
#	printer.smuff.feeder2			(bool) 		True = triggered
#	printer.smuff.fwinfo			(string)	Same as with M115 GCode command
#	printer.smuff.isbusy			(bool)		True if SMuFF is doing stuff
#	printer.smuff.iserror			(bool)		True if the last command processed did fail 
#	printer.smuff.isprocessing		(bool)		True while processing stuff
#	printer.smuff.isconnected		(bool)		True when connected through serial port
#	printer.smuff.isidle			(bool)		True if SMuFF is in idle state
#	printer.smuff.sdstate			(bool) 		True if SD-Card on SMuFF is inserted
#	printer.smuff.lidstate			(bool) 		True if Lid is closed
#	printer.smuff.hascutter			(bool)		True if Filament-Cutter is configured (see below)
#	printer.smuff.haswiper			(bool)		True if Wiper is configured (see below)
#	printer.smuff.device			(string)	Name of the SMuFF
#
#
# The configuration takes place in 'smuff.cfg', which contains the configuration for this
# module, as well as the tool change GCodes, as the following example shows.
# Add a [include smuff.cfg] line into your 'printer.cfg' to use this module.
#
#   [smuff]
#   serial=/dev/serial/by-id/... or /dev/ttySMuFF if set up accordingly
#   baudrate=115200
#   serialTimeout=10
#   commandTimeout=25
#   toolchangeTimeout=90
#   autoload=yes
#   autoconnect=yes
#	hasCutter=yes
#	hasWiper=no
#
# The GCode macros PRE_TC and POST_TC are being called from within the Tn GCodes accordingly.
# PRE_TC macros at least have to contain the GCode 'M84 E', which turns off the printers extruder
# stepper motor, which is essential for the SMuFF to be able to safely switch the relay.
# POST_TC macros may contain any GCode to prepare the printer for resuming the print.
#
#   [gcode_macro PRE_TC]
#   gcode:
#       M84 E    # mandantory; switch off extruder motor
#       M117 Changing tool
#
#   [gcode_macro POST_TC]
#   gcode:
#       M117 Tool change done.
#
# Tool change macros (T0-T11) macros will call the internal function SMUFF_TOOL_CHANGE with
# the according tool as parameter. Keep in mind, you'll need as many macros as you have tools
# on your SMuFF. Although, it doesn't hurt configuring the max. number of tools, which in
# this case is 12 (0-11).
#
#   [gcode_macro T0]
#   gcode:
#       PRE_TC
#       SMUFF_TOOL_CHANGE T=0
#       POST_TC
#   ...
#
#   [gcode_macro T11]
#   gcode:
#       PRE_TC
#       SMUFF_TOOL_CHANGE T=11
#       POST_TC
#---------------------------------------------------------------------------------------------

import json
import logging
import re
import sys
import time
import traceback
try:
    import serial
except ImportError:
    logging.critical("SMuFF: Python library 'pySerial' is missing. Please use 'pip install pyserial' first!")

from threading import Thread, Lock, Event

FWINFO		= "M115"        		# SMuFF GCode to query firmware info
PERSTATE    = "M155 S1"     		# SMuFF GCode for enabling sending periodical states
WIPE		= "G12"         		# SMuFF GCode to wipe nozzle
CUT			= "G12 C"        		# SMuFF GCode to cut filament
SETSERVO	= "M280 P{0} S{1}" 		# SMuFF GCode to position a servo
LIDOPEN		= "M280 R0"     		# SMuFF GCode to open Lid servo
LIDCLOSE	= "M280 R1"     		# SMuFF GCode to close lid servo
TOOL		= "T"           		# SMuFF GCode to swap tools
HOME 		= "G28"					# SMuFF GCode for homing
GETCONFIG 	= "M503 S{0}W"			# SMuFF Gcode to query configuration settings (in JSON format)
SETPARAM 	= "M205 P\"{0}\"S{1}"	# SMuFF GCode for setting config params
LOAD 		= "M700"				# SMuFF GCode to load active tool
UNLOAD 		= "M701"				# SMuFF GCode to unload active tool
MOTORSOFF	= "M18"					# SMuFF GCode to turn stepper motors off
UNJAM 		= "M562"				# SMuFF GCode to reset the Feeder jammed flag
RESET 		= "M999"				# SMuFF GCode to reset the device

AUTOLOAD	= "S1"          		# additional parameter for auto load after tool swap

S_ON		= "ON"          		# Parameter in 'states:'
S_OFF		= "OFF"         		# Parameter in 'states:'
S_YES 		= "YES"
S_NO 		= "NO"
S_REMOVED	= "REMOVED"
S_INSERTED	= "INSERTED"
S_OPENED	= "OPENED"
S_CLOSED	= "CLOSED"

NOTCONN		= "SMuFF is not yet connected. Use SMUFF_CONNECT first and check 'smuff.cfg' for the correct serial settings."

# Response srings coming from SMuFF
R_START			= "start\n"
R_OK			= "ok\n"
R_ECHO			= "echo:"
R_DEBUG			= "dbg:"
R_ERROR			= "error:"
R_BUSY			= "busy"
R_STATES		= "states:"
R_UNKNOWNCMD	= "Unknown command:"
R_JSON			= "{"
R_JSONCAT		= "/*"
R_FWINFO		= "FIRMWARE_"

# Action commands coming from/sent to the SMuFF
ACTION_CMD		= "//action:"
ACTION_WAIT		= "WAIT"
ACTION_CONTINUE	= "CONTINUE"
ACTION_ABORT	= "ABORT"
ACTION_PING		= "PING"
ACTION_PONG		= "PONG"

# Klipper printer states
ST_IDLE			= "Idle"
ST_PRINTING		= "Printing"
ST_READY		= "Ready"

# GCode parameters
P_TOOL			= "T"       		# used in SMUFF_TOOL_CHANGE
P_TOOL2			= "TOOL"       		# used in SMUFF_TOOL_CHANGE
P_SERVO			= "SERVO"   		# used in SMUFF_SET_SERVO (i.e. SERVO=0)
P_ANGLE			= "ANGLE"   		# used in SMUFF_SET_SERVO (i.e. ANGLE=95)
P_GCODE			= "GCODE"   		# used in SMUFF_SEND (i.e. GCODE="M119")
P_PARAM			= "PARAM" 			# used in SMUFF_PARAM (i.e. PARAM="BowdenLen")
P_PARAMVAL		= "VALUE"  			# used in SMUFF_PARAM (i.e. VALUE="620")

# Wrapper class for logging with a prefix
class SLogger:
	def __init__(self, prefix):
		self._prefix = prefix
		pass

	def info(self, message):
		logging.info(self._prefix.format(message))

	def error(self, message):
		logging.error(self._prefix.format(message))

	def debug(self, message):
		logging.debug(self._prefix.format(message))


class SMuFF:

	def __init__(self, config, logger):
		self._log 				= logger
		self._serial            = None      # serial instance
		self._serialPort       	= None      # serial port device name
		self._baudrate          = 0         # serial port baudrate
		self._timeout           = 0.0       # communication timeout
		self._cmdTimeout        = 0.0       # command timeout
		self._tcTimeout         = 0.0       # tool change timeout
		self._toolCount         = 0
		self._autoConnect       = False
		self._serLock			= Lock()	# lock object for reading/writing

		self._printer = config.get_printer()
		try:
			# is this really needed?
			self.pause_resume = self._printer.load_object(config, "pause_resume")
		except config.error:
			raise self._printer.config_error("SMuFF requires [pause_resume] to work, please add it to your config!")

		# register GCodes for SMuFF
		self.gcode = self._printer.lookup_object("gcode")
		self.gcode.register_command("SMUFF_CONN",           self.cmd_connect,     	"Connect to the SMuFF")
		self.gcode.register_command("SMUFF_DISC",           self.cmd_disconnect,  	"Disconnect from the SMuFF")
		self.gcode.register_command("SMUFF_CONNECTED",      self.cmd_connected,  	"Show current connection status")
		self.gcode.register_command("SMUFF_CUT",            self.cmd_cut,         	"Cut filament")
		self.gcode.register_command("SMUFF_WIPE",           self.cmd_wipe,        	"Wipe nozzle")
		self.gcode.register_command("SMUFF_LID_OPEN",       self.cmd_lid_open,    	"Open lid servo")
		self.gcode.register_command("SMUFF_LID_CLOSE",      self.cmd_lid_close,   	"Close lid servo")
		self.gcode.register_command("SMUFF_SET_SERVO",      self.cmd_servo_pos,   	"Position a servo")
		self.gcode.register_command("SMUFF_TOOL_CHANGE",    self.cmd_tool_change, 	"Change the current tool")
		self.gcode.register_command("SMUFF_INFO",           self.cmd_fw_info,     	"Query the firmware info from SMuFF")
		self.gcode.register_command("SMUFF_STATUS",         self.cmd_get_states,  	"Query the status from SMuFF")
		self.gcode.register_command("SMUFF_SEND",           self.cmd_gcode,       	"Send GCode to the SMuFF")
		self.gcode.register_command("SMUFF_PARAM",          self.cmd_param,       	"Send configuration parameters to the SMuFF")
		self.gcode.register_command("SMUFF_MATERIALS",      self.cmd_materials,     "Query the materials configured on the SMuFF")
		self.gcode.register_command("SMUFF_SWAPS",      	self.cmd_swaps,     	"Query the tool swaps configured on the SMuFF")
		self.gcode.register_command("SMUFF_LIDMAPPINGS",   	self.cmd_lidmappings,   "Query the lid servo mappings configured on the SMuFF")
		self.gcode.register_command("SMUFF_LOAD",   		self.cmd_load,   		"Load filament on active tool on the SMuFF")
		self.gcode.register_command("SMUFF_UNLOAD",   		self.cmd_unload,   		"Unload filament from active tool on the SMuFF")
		self.gcode.register_command("SMUFF_HOME",   		self.cmd_home,   		"Home Selector (and Revolver if configured) on the SMuFF")
		self.gcode.register_command("SMUFF_MOTORS_OFF", 	self.cmd_motors_off, 	"Turn stepper motors on the SMuFF off")
		self.gcode.register_command("SMUFF_CLEAR_JAM",		self.cmd_clear_jam, 	"Resets the Feeder Jammed flag on the SMuFF")
		self.gcode.register_command("SMUFF_RESET",			self.cmd_reset, 		"Resets the SMuFF")

		# get configuration
		self._serialPort = config.get("serial")
		if not self._serialPort:
			raise config.error("No serial port defined for SMuFF. Put serial=/dev/serial/xxx into 'smuff.cfg', where xxx is the 'by-id' value of the tty the SMuFF is connected to.")
		self._baudrate      = config.getint("baudrate", default=115200)
		self._timeout       = config.getfloat("serialTimeout", default=10.0)
		self._cmdTimeout    = config.getfloat("commandTimeout", default=25.0)
		self._tcTimeout     = config.getfloat("toolchangeTimeout", default=90.0)
		self._autoConnect   = config.get("autoConnect").upper() == S_YES

		self._reset()
		self._autoload = config.get("autoload").upper() == S_YES
		self._hasCutter = config.get("hasCutter").upper() == S_YES 		# will be eventually overwritten by the SMuFF config
		self._hasWiper = config.get("hasWiper").upper() == S_YES

	def _reset(self):
		self._fw_info 			= "?"		# SMuFFs firmware info
		self._curTool 			= "T-1"		# the current tool
		self._pre_tool 			= "T-1"		# the previous tool
		self._pendingTool 		= -1		# the tool on a pending tool change
		self._selector 			= False		# status of the Selector endstop
		self._revolver 			= False		# status of the Revolver endstop
		self._feeder 			= False		# status of the Feeder endstop
		self._feeder2			= False		# status of the 2nd Feeder endstop
		self._isBusy			= False		# flag set when SMuFF signals "Busy"
		self._isError			= False		# flag set when SMuFF signals "Error" 
		self._response			= None		# the response string from SMuFF
		self._wait_requested	= False 	# set when SMuFF requested a "Wait" (in case of jams or similar)
		self._abort_requested	= False		# set when SMuFF requested a "Abort"
		self._lastSerialEvent	= 0 		# last time (in millis) a serial receive took place
		self._isProcessing		= False		# set when SMuFF is supposed to be busy
		self._isReconnect 	    = False		# set when trying to re-establish serial connection
		self._isConnected       = False     # set after connection has been established
		self._autoload          = True      # set to load new filament automatically after swapping tools 
		self._serEvent			= Event()	# event raised when a valid response has been received
		self._sdcard            = False     # set to True when SD-Card on SMuFF was removed
		self._cfgChange         = False     # set to True when SMuFF configuration has changed
		self._lid               = False     # set to True when Lid on SMuFF is open
		self._isIdle            = False     # set to True when SMuFF is idle
		self._usesTmc           = False     # set to True when SMuFF uses TMC drivers
		self._tmcWarning        = False     # set to True when TMC drivers on SMuFF report warnings
		self._lastResponse     	= ""		# last response SMuFF has sent (multiline)
		self._hasCutter 		= False 	# flag set if Filament-Cutter is installed
		self._hasWiper 			= False 	# flag set if Wiper is installed
		self._device 			= "" 		# current name of the SMuFF
		if self._serial:
			self.close_serial()
		self._sreader 			= None 
		self._sconnector		= None 

    #
    # SMUFF_CONN
    #
	def cmd_connect(self, gcmd=None, autoConnect=None):
		if self._isConnected:
			self.gcode.respond_info("SMuFF is already connected")
			return True
		try:
			self.connect_SMuFF(gcmd)
			if autoConnect and autoConnect ==  True:
				return True
		except Exception as err:
			self.gcode.respond_info("Connecting to SMuFF has thrown an exception:\n\t{0}".format(err))
			return False

		if self._isConnected:
			self.gcode.respond_info("Connected to SMuFF")
			return True
		return False

    #
    # SMUFF_DISC
    #
	def cmd_disconnect(self, gcmd=None):
		try:
			self.close_serial()
			self.gcode.respond_info("Disconnected from SMuFF")
		except Exception as err:
			self.gcode.respond_info("Disconnecting from SMuFF has thrown an exception:\n\t{0}".format(err))

		self._serial = None
		self._isConnected = False

    #
    # SMUFF_CONNECTED
    #
	def cmd_connected(self, gcmd):
		if self._isConnected:
			self.gcode.respond_info("SMuFF is connected on {}".format(self._serialPort))
		else:
			self.gcode.respond_info("SMuFF is currently not connected")

    #
    # SMUFF_CUT
    #
	def cmd_cut(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		#self.gcode.respond_info("Cutting filament...")
		self.send_SMuFF(CUT)

    #
    # SMUFF_WIPE
    #
	def cmd_wipe(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		#self.gcode.respond_info("Wiping nozzle...")
		self.send_SMuFF(WIPE)

    #
    # SMUFF_LID_OPEN
    #
	def cmd_lid_open(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		#self.gcode.respond_info("Opening lid...")
		self.send_SMuFF(LIDOPEN)

    #
    # SMUFF_LID_CLOSE
    #
	def cmd_lid_close(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		#self.gcode.respond_info("Closing lid...")
		self.send_SMuFF(LIDCLOSE)

    #
    # SMUFF_SET_SERVO
    #
	def cmd_servo_pos(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		servo = gcmd.get_int(P_SERVO, default=1) 	# Lid servo by default
		pos = gcmd.get_int(P_ANGLE, default=90)
		if pos < 0 or pos > 180:
			gcmd.respond_info("Servo position must be between 0 and 180")
			return
		#self.gcode.respond_info("Positioning servo {0} to {1} deg.".format(servo, pos))
		self.send_SMuFF(SETSERVO.format(servo, pos))

    #
    # SMUFF_TOOL_CHANGE
    #
	def cmd_tool_change(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		activeTool = self.parse_tool_number(self._curTool)
		self._pendingTool = gcmd.get_int(P_TOOL, default=-1)
		if self._pendingTool == -1:
			self._pendingTool = gcmd.get_int(P_TOOL2, default=-1)
			if self._pendingTool == -1:
				self.gcode.respond_info("SMuFF tool change: No tool number specified (T = n)")
				return
		if self._pendingTool > self._toolCount:
			self.gcode.respond_info("SMuFF tool change: Selected tool (T{0}) exceeds existing tools ({1})".format(self._pendingTool, self._toolCount))
			self._pendingTool = -1
			return
		if activeTool != self._pendingTool:
			self._pre_tool = self._curTool
			self._log.info("Swapping tool from T{0} to T{1}".format(activeTool, self._pendingTool))
			self.send_SMuFF_and_wait(TOOL + str(self._pendingTool) + (AUTOLOAD if self._autoload else ""))
		else:
			self.gcode.respond_info("Selected tool (T{0}) is already loaded. Skipping tool change.".format(self._pendingTool))

    #
    # SMUFF_INFO
    #
	def cmd_fw_info(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.gcode.respond_info("SMuFF firmware info:\n{0}".format(self._fw_info))

    #
    # SMUFF_STATES
    #
	def cmd_get_states(self, gcmd=None):
		str = "SMuFF state info:\n"
		str += "Connected:\t{}\n".format(S_YES if self._isConnected else S_NO)
		str += "Device:\t\t{}\n".format(self._device)
		str += "Tools:\t\t{}\n".format(self._toolCount)
		str += "Active Tool:\t{}\n".format(self._curTool)
		str += "Selector:\t{}\n".format(S_ON if self._selector else S_OFF)
		str += "Feeder:\t\t{}\n".format(S_ON if self._feeder else S_OFF)
		str += "Feeder 2:\t{}\n".format(S_ON if self._feeder2 else S_OFF)
		str += "Lid:\t\t{}\n".format(S_CLOSED if self._lid else S_OPENED)
		str += "SD-Card:\t{}\n".format(S_REMOVED if self._sdcard else S_INSERTED)
		str += "Idle:\t\t{}\n".format(S_YES if self._isIdle else S_NO)
		str += "Config changed:\t{}\n".format(S_YES if self._cfgChange else S_NO)
		self.gcode.respond_info(str)

    #
    # SMUFF_SEND
    #
	def cmd_gcode(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		_gcode = gcmd.get(P_GCODE)
		if not _gcode:
			gcmd.respond_info("SMuFF GCode: No GCode specified (G = '...')")
			return
		response = self.send_SMuFF_and_wait(_gcode)
		if response:
			gcmd.respond_info("SMuFF responded with: {}".format(response))

    #
    # SMUFF_PARAM
    #
	def cmd_param(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		_param = gcmd.get(P_PARAM)
		_paramVal = gcmd.get(P_PARAMVAL)
		if not _param:
			gcmd.respond_info("No parameter name specified (P = '...')")
			return
		if not _paramVal:
			gcmd.respond_info("No parameter value specified (V = '...')")
			return
		response = self.send_SMuFF_and_wait(SETPARAM.format(_param,_paramVal))
		if self._isError:
			gcmd.respond_info("SMuFF responded with error! [{}]".format(response))

    #
    # SMUFF_MATERIALS
    #
	def cmd_materials(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(GETCONFIG.format(5))

    #
    # SMUFF_SWAPS
    #
	def cmd_swaps(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(GETCONFIG.format(6))

    #
    # SMUFF_LIDMAPPINGS
    #
	def cmd_lidmappings(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(GETCONFIG.format(4))

    #
    # SMUFF_LOAD
    #
	def cmd_load(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		activeTool = self.parse_tool_number(self._curTool)
		if activeTool != -1:
			response = self.send_SMuFF_and_wait(LOAD)
		if self._isError:
			gcmd.respond_info("SMuFF responded with error! [{}]".format(response))

    #
    # SMUFF_UNLOAD
    #
	def cmd_unload(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		activeTool = self.parse_tool_number(self._curTool)
		if activeTool != -1:
			response = self.send_SMuFF_and_wait(UNLOAD)
		if self._isError:
			gcmd.respond_info("SMuFF responded with error! [{}]".format(response))

    #
    # SMUFF_HOME
    #
	def cmd_home(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(HOME)

    #
    # SMUFF_MOTORS_OFF
    #
	def cmd_motors_off(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(MOTORSOFF)

    #
    # SMUFF_CLEAR_JAM
    #
	def cmd_clear_jam(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(UNJAM)

    #
    # SMUFF_RESET
    #
	def cmd_reset(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(NOTCONN)
			return
		self.send_SMuFF(RESET)

	#
	# Set status values to be used within Klipper scripts
	#
	def get_status(self, eventtime=None):
		values = {
			"tools":   		self._toolCount,
			"activetool":   self.parse_tool_number(self._curTool),
			"pendingtool":  self._pendingTool,
			"selector":     self._selector,
			"revolver":     self._revolver,
			"feeder":       self._feeder,
			"feeder2":      self._feeder2,
			"fwinfo":       self._fw_info,
			"isbusy":       self._isBusy,
			"iserror":      self._isError,
			"isprocessing": self._isProcessing,
			"isconnected":	self._isConnected,
			"isidle": 		self._isIdle,
			"sdstate": 		self._sdcard,
			"lidstate": 	self._lid,
			"hascutter":	self._hasCutter,
			"haswiper":		self._hasWiper,
			"device": 		self._device
		}
		return values
	

	##~~ SMuFF helper functions

	def connect_SMuFF(self, gcmd=None):
		self._isConnected = False

		try:
			self.open_serial()
			if self._serial:
				self._isConnected = True
			else:
				self._log.info("Opening serial {0} for SMuFF has failed".format(self._serialPort))
				return
		except Exception as err:
			self._log.error("Connecting to SMuFF has thrown an exception:\n\t{0}".format(err))

		if self._isReconnect:
			self._isReconnect = False
			return
		self.init_SMuFF()

	#
	# Opens the serial port for the communication with the SMuFF
	#
	def open_serial(self):
		try:
			self._log.info("Opening serial port {0}".format(self._serialPort))
			self._serial = serial.Serial(self._serialPort, self._baudrate, timeout=self._timeout, write_timeout=0)
			if self._serial and self._serial.is_open:
				self._log.info("Serial port opened")
				try:
					# set up a separate task for reading the incoming SMuFF messages
					self._sreader = Thread(target=self.serial_reader, name="TReader")
					self._sreader.daemon = True
					self._sreader.start()
					self._log.info("Serial reader thread running... ({0})".format(self._sreader))
				except:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
					self._log.error("Unable to start serial reader thread: ".join(tb))

		except (OSError, serial.SerialException):
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Can't open serial port {0}! Exc: {1}".format(self._serialPort, tb))

	#
	# Closes the serial port and cleans up resources
	#
	def close_serial(self):
		if not self._serial:
			self._log.info("Serial wasn't initialized, nothing to do here")
			return
		# discard reader thread
		self._sreader = None
		# close the serial port
		try:
			if self._serial and self._serial.is_open:
				self._serial.close()
			self._log.debug("Serial port {0} closed".format(self._serial.port))
		except (OSError, serial.SerialException):
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Can't close serial port {0}! Exc: {1}".format(self._serial.port, tb))

	#
	# Serial reader thread
	#
	def serial_reader(self):
		self._log.info("Entering serial reader on {0}".format(self._serial.port))
		cnt = 0
		# this loop basically runs forever, unless _stop_serial is set or the
		# serial port gets closed
		while 1:
			if self._serial and self._serial.is_open:
				try:
					b = self._serial.in_waiting
					if b > 0:
						try:
							self._serLock.acquire()
							data = self._serial.readline().decode("ascii")	# read to EOL
							self._serLock.release()
							self.parse_serial_data(data)
						except:
							exc_type, exc_value, exc_traceback = sys.exc_info()
							tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
							self._log.error("Serial reader error: ".join(tb))
				except serial.SerialException as err:
					self._serLock.release()
					self._log.error("Serial reader has thrown an exception:\n\t".format(err))
				except serial.SerialTimeoutException as err:
					self._serLock.release()
					self._log.error("Serial reader has timed out:\n\t".format(err))
			else:
				self._serLock.release()
				self._log.error("Serial port {0} has been closed".format(self._serial.port))
				break

			cnt += 1
			time.sleep(0.01)    # sleep 10 milliseconds
			if cnt >= 6000:
				# send some "I'm still alive" signal every 60 seconds (for debugging purposes only)
				self._log.debug("Serial Reader Ping...")
				cnt = 0

		self._log.error("Exiting serial port receiver")

	#
	# Method which starts serial_connector() in the background.
	#
	def start_connector(self):
		try:
			# set up a separate task for connecting to the SMuFF
			self._sconnector = Thread(target=self.serial_connector, name="TConnector")
			self._sconnector.daemon=True
			self._sconnector.start()
			self._log.info("Serial connector thread running... ({0})".format(self._sconnector))
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Unable to start serial connector thread: ".join(tb))

	#
	# Serial connector thread
	#
	def serial_connector(self):
		self._log.info("Entering serial port connector for {0}".format(self._serialPort))
		time.sleep(3)

		while 1: 
			if self.cmd_connect(autoConnect=True) == True:
				break
			time.sleep(1)
			self._log.info("Serial connector looping...")

		# as soon as the connection has been established, cancel the connector thread
		self._log.info("Exiting serial connector")
		self._sconnector = None
	
    #
	# Sends data to SMuFF
    #
	def send_SMuFF(self, data):
		now = nowMS()
		if (self._lastSerialEvent > 0 and (now - self._lastSerialEvent)/1000 > self._tcTimeout):
			self._log.error("Possible communication error... last event was {0} seconds ago".format((now-self._lastSerialEvent)/1000))
			self.close_serial()
			self._isReconnect = True
			self.connect_SMuFF()

		if self._serial and self._serial.is_open:
			try:
				b = bytearray(len(data)+2)
				b = "{0}\n".format(data).encode("ascii")
				# lock down the reader thread just in case 
				# (shouldn't be needed at all, since simultanous read/write operations should
				# be no big deal)
				self._serLock.acquire()
				n = self._serial.write(b)
				self._serLock.release()
				self._log.debug("Sent {1} bytes: [{0}]".format(b, n))
				return True
			except (OSError, serial.SerialException):
				self._serLock.release()
				self._log.error("Unable to send command to SMuFF")
				self.close_serial()
				self._log.info("Trying a reconnect")
				self.connect_SMuFF()
				return False
		else:
			self._log.error("Serial not open, can't send data")
			return False

    #
	# Sends data to SMuFF and will wait for a response (which in most cases is 'ok')
    #
	def send_SMuFF_and_wait(self, data):

		if data.startswith(TOOL):
			timeout = self._tcTimeout 	# wait max. 30 seconds for a response while swapping tools
			tm = "tool change"
		else:
			timeout = self._cmdTimeout	# wait max. 5 seconds for other operations
			tm = "command"
		done = False
		resp = None
		self.set_busy(False)		# reset busy and
		self.set_error(False)		# error flags
		self.set_processing(True)	# SMuFF is currently doing something

		if self.send_SMuFF(data) == False:
			return None

		while not done:
			self._serEvent.clear()
			is_set = self._serEvent.wait(timeout)
			if is_set:
				self._log.info("To [{0}] SMuFF says [{1}] (is_error = {2})".format(data, self._response, self._isError))
				resp = self._response
				if self._response == None or self._isError:
					done = True
				elif not self._response.startswith(R_ECHO):
					done = True

				self._response = None
			else:
				self._log.info("No event received, aborting. Try increasing the {} timeout.".format(tm))
				if self._isBusy == False:
					done = True

		self.set_processing(False)	# SMuFF is not supposed to do anything
		return resp

	def init_SMuFF(self):
		# request firmware info from SMuFF 
		self.send_SMuFF(FWINFO)
		# turn periodical states sending on
		self.send_SMuFF(PERSTATE)
		# query some configuration settings
		self.send_SMuFF(GETCONFIG.format(1))

	def set_processing(self, processing):
		self._isProcessing = processing

	def set_busy(self, busy):
		self._isBusy = busy

	def set_error(self, error):
		self._isError = error

	def set_response(self, response):
		if not response == None:
			self._response = response.rstrip("\n")
		else:
			self._response = ""
		self._lastResponse = ""

	def hex_dump(self, s):
		self._log.info(":".join("{:02x}".format(ord(c)) for c in s))

    #
    # Parses the states periodically sent by the SMuFF
    #  
	def parse_json(self, data):
		#self._log.info("Parse JSON:\n\t[{0}] -> {1}".format(data, self._jsonCat))
		if data:
			resp = ""
			try:
				cfg = json.loads(data)
				# basic configuration
				if cfg and self._jsonCat == "basic":
					self._device = cfg["Device"]
					self._toolCount = cfg["Tools"]
					self._hasCutter = cfg["UseCutter"]
				
				# materials configuration
				if cfg and self._jsonCat == "materials":
					for i in range(self._toolCount):
						t = "T"+str(i)
						resp += "Tool {0} is '{2} {1}' with a purge factor of {3}%\n".format(i, cfg[t]["Material"], cfg[t]["Color"], cfg[t]["PFactor"])
				
				# tool swapping configuration
				if cfg and self._jsonCat == "tool swaps":
					for i in range(self._toolCount):
						resp += "Tool {0} is assigned to tray {1}\n".format(i, cfg["T"+str(i)])
				
				# servo mapping configuration
				if cfg and self._jsonCat == "servo mapping":
					for i in range(self._toolCount):
						resp += "Tool {0} closed @ {1} deg.\n".format(i, cfg["T"+str(i)]["Close"])
				
				if len(resp):
					self.gcode.respond_info(resp)

			except Exception as err:
				self._log.error("Parse JSON for category {1} has thrown an exception:\n\t{0}".format(err, self._jsonCat))

    #
    # Parses the states periodically sent by the SMuFF
    #  
	def parse_states(self, states):
		#self._log.info("States received: [" + states + "]")
		if len(states) == 0:
			return False

		# Note: SMuFF sends periodically states in this notation: 
		# 	"echo: states: T: T4  S: off  R: off  F: off  F2: off  TMC: -off  SD: off  SC: off  LID: off  I: off  SPL: 0"
		for m in re.findall(r'([A-Z]{1,3}[\d|:]+).(\+?\w+|-?\d+|\-\w+)+',states):
			if   m[0] == "T:":                          # current tool
				self._curTool      	= m[1].strip()
			elif m[0] == "S:":                          # Selector endstop state
				self._selector      = m[1].strip() == S_ON.lower()
			elif m[0] == "R:":                          # Revolver endstop state
				self._revolver      = m[1].strip() == S_ON.lower()
			elif m[0] == "F:":                          # Feeder endstop state
				self._feeder        = m[1].strip() == S_ON.lower()
			elif m[0] == "F2:":                         # DDE-Feeder endstop state
				self._feeder2       = m[1].strip() == S_ON.lower()
			elif m[0] == "SD:":                         # SD-Card state
				self._sdcard        = m[1].strip() == S_ON.lower()
			elif m[0] == "SC:":                         # Settings Changed
				self._cfgChange     = m[1].strip() == S_ON.lower()
			elif m[0] == "LID:":                        # Lid state
				self._lid           = m[1].strip() == S_ON.lower()
			elif m[0] == "I:":                          # Idle state
				self._isIdle        = m[1].strip() == S_ON.lower()
			elif m[0] == "TMC:":                        # TMC option
				v = m[1].strip()
				self._usesTmc = v.startswith("+")
				self._tmcWarning = v[1:] == S_ON.lower()
			elif m[0] == "SPL:":                        # Splitter load state
				self._spl = int(m[1].strip())
			#else:
				#	self._log.error("Unknown state: [" + m[0] + "]")
		return True

    #
	# Converts the textual 'Tn' into a tool number
    #
	def parse_tool_number(self, tool):
		if not tool or tool == "":
			return -1
		try:
			#self._log.info("Tool: [{}]".format(tool))
			return int(re.findall(r'[-\d]+', tool)[0])
		except Exception as err:
			self._log.error("Can't parse tool number in {0}:\n\t{1}".format(tool, err))
		return -1

    #
	# Parses the response we get from the SMuFF
    #
	def parse_serial_data(self, data):
		if data == None or len(data) == 0 or data == "\n":
			return

		#self._log.info("Raw data: [{0}]".format(data.rstrip("\n")))

		self._lastSerialEvent = nowMS()
		self._serEvent.clear()

		# after first connect the response from the SMuFF is supposed to be 'start'
		if data.startswith(R_START):
			self._log.info("\"start\" response received")
			time.sleep(3)
			self.init_SMuFF()
			return

		if data.startswith(R_ECHO):
			# don't process any general debug messages
			if data[6:].startswith(R_DEBUG):
				self._log.debug("SMuFF has sent a debug response: [" + data.rstrip() + "]")
			# but do process the tool/endstop states
			elif data[6:].startswith(R_STATES):
				self._lastResponse = ""
				self.parse_states(data.rstrip())
			# and register whether SMuFF is busy
			elif data[6:].startswith(R_BUSY):
				err = "SMuFF has sent a busy response: [" + data.rstrip() + "]"
				self._log.debug(err)
				self.gcode.respond_info(err)
				self.set_busy(True)
			return

		if data.startswith(R_ERROR):
			err = "SMuFF has sent a error response: [" + data.rstrip() + "]"
			self._log.info(err)
			self.gcode.respond_info(err)
			# maybe the SMuFF has received garbage
			if data[7:].startswith(R_UNKNOWNCMD):
				self._serial.flushOutput()
			self.set_error(True)
			return

		if data.startswith(ACTION_CMD):
			#self._log.info("SMuFF has sent an action request: [" + data.rstrip() + "]")
			# what action is it? is it a tool change?
			if data[10:].startswith(TOOL):
				tool = self.parse_tool_number(data[10:])
				# only if the printer isn't printing
				idle_timeout = self._printer.lookup_object("idle_timeout")
				state = idle_timeout.state
				self._log.info("SMuFF requested an action while printer in state '{0}'".format(state))
				if state == ST_PRINTING:
					# query the heater 
					heater = self._printer.lookup_object("heater")
					try:
						if heater.extruder.can_extrude:
							self._log.debug("Extruder is up to temp.")
							self._printer.change_tool("tool{0}".format(tool))
							self.send_SMuFF("{0} T: OK".format(ACTION_CMD))
						else:
							self._log.error("Can't change to tool {0}, nozzle not up to temperature".format(tool))
							self.send_SMuFF("{0} T: \"Nozzle too cold\"".format(ACTION_CMD))
					except:
						self._log.error("Can't query temperatures. Aborting.")
						self.send_SMuFF("{0} T: \"No nozzle temp. avail.\"".format(ACTION_CMD))
				else:
					self._log.error("Can't change to tool {0}, printer not ready or printing".format(tool))
					self.send_SMuFF("{0} T: \"Printer not ready\"".format(ACTION_CMD))

			if data[10:].startswith(ACTION_WAIT):
				self._wait_requested = True
				self._log.info("waiting for SMuFF to come clear...")

			if data[10:].startswith(ACTION_CONTINUE):
				self._wait_requested = False
				self._abort_requested = False
				self._log.info("continuing after SMuFF cleared...")

			if data[10:].startswith(ACTION_ABORT):
				self._wait_requested = False
				self._abort_requested = True
				self._log.info("SMuFF is aborting action operation...")

			if data[10:].startswith(ACTION_PONG):
				self._log.info("PONG received from SMuFF")
			return

		if data.startswith(R_JSONCAT):
			self._jsonCat = data[2:].rstrip("*/\n").strip(" ").lower()
			#self._log.info("JSON Category: [{}]".format(self._jsonCat))
			return

		if data.startswith(R_JSON):
			self.parse_json(data)
			self._jsonCat = None
			return

		if data.startswith(R_FWINFO):
			self._fw_info = data.rstrip("\n")
			self.gcode.respond_info("SMuFF: FW-Info:\n{0}".format(self._fw_info))
			return

		if data.startswith(R_OK):
			if self._isError:
				self.set_response(None)
			else:
				self.set_response(self._lastResponse)
			self._serEvent.set()
			return

		# store the last response(s) before the "ok"
		if data:
			self._lastResponse = self._lastResponse + str(data)
		self._log.debug("Received response: [{0}]".format(self._lastResponse))

#
# Helper function to retrieve time in milliseconds 
#
def nowMS():
	return int(round(time.time() * 1000))

#
# Main entry point; Creates a new instance of this module.
#  
def load_config(config):
	logger = SLogger("SMuFF: {0}")

	try:
		instance = SMuFF(config, logger)
		logger.info("Module instance successfully created")
		if instance and instance._autoConnect:
			logger.info("Auto connecting...")
			instance.start_connector()
		return instance
	except Exception as err:
		logger.error("Unable to create module instance.\n\t{0}".format(err))
		return None