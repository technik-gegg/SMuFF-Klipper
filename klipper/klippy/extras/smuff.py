#---------------------------------------------------------------------------------------------
# SMuFF Klipper Module
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
#	SMUFF_CONNECTED		- Show current connection status (see also: SMUFF_STATUS)
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
# 	SMUFF_VERSION		- Query the SMuFF module version
# 	SMUFF_RESET_AVG		- Resets the tool change statistics
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
#	printer.smuff.materials			(array)		Two dimensional array of type materials
#	printer.smuff.swaps				(array)		Array of tool swaps
#	printer.smuff.lidmappings		(array)		Array of lid mappings
#	printer.smuff.version			(float)		Module version info
#	printer.smuff.fwversion			(string)	The SMuFF firmware version
#	printer.smuff.fwmode			(string)	The configured SMuFF mode
#	printer.smuff.fwoptions			(string)	The configured SMuFF options
#	printer.smuff.loadstate			(int)		The current tool filament load state
#	printer.smuff.isdde				(bool)		True if DDE is configured
#	printer.smuff.hassplitter		(bool)		True if Splitter Option is configured
#
#
# The configuration takes place in 'smuff.cfg', which contains the configuration for this
# module, as well as the tool change GCodes, as the following example shows.
# Add a [include smuff.cfg] line into your 'printer.cfg' to use this module.
#
#   [smuff]
#   serial=/dev/serial/by-id/... or /dev/ttySMuFF if it has been set up accordingly
#   baudrate=115200
#   serialTimeout=10
#   autoConnectSerial=yes
#   commandTimeout=25
#   toolchangeTimeout=90
#   autoLoad=yes
#	hasCutter=yes
#	hasWiper=no
#	debug=no
#
#
# PRE_TOOLCHANGE and POST_TOOLCHANGE will be called from within
# the module in order to prepare the printer for a tool change /
# resume printing.
#
# Basically it's pausing/resuming the print but you can put in
# different commands, such like wiping, purging or ramming,
# if needed.
#
# PARK_TOOLHEAD macro sets the toolhead to a save position for
# the tool change. Modify the positions to suite your printer
# if needed.
#
# [gcode_macro PRE_TOOLCHANGE]
# description: Macro called from SMUFF_TOOL_CHANGE for pre-processing. Don't call it via console or script!
# gcode:
#   # the SMuFF module will provide a parameter T for the current tool in case
#   # you want to evalute those before pausing the print
#   #   { action_respond_info("Tool change to 'T%s' pending" % params.T|int) }
#   # pause the print first
#   PAUSE_BASE
#   PARK_TOOLHEAD
#   # then switch off extruder motor (it's mandatory!)
#   SET_STEPPER_ENABLE STEPPER=extruder ENABLE=0

# [gcode_macro POST_TOOLCHANGE]
# description: Macro called from SMUFF_TOOL_CHANGE for post-processing. Don't call it via console or script!
# gcode:
#   # the SMuFF module will provide two parameters, P for the previous tool, T for the current tool
#   # in case you want to evalute those before resuming
#   #   { action_respond_info("Tool change from 'T%s' to 'T%s' done" % params.P|int, params.T|int) }
#   # switch extruder motor back on
#   SET_STEPPER_ENABLE STEPPER=extruder ENABLE=1
#   # then resume printing
#   RESUME_BASE
#
# [gcode_macro PARK_TOOLHEAD]
# description: Parks the toolhead before a tool change.
# gcode:
#   # set park position for x and y; default is the max. position
#   # taken from your printer.cfg
#   {% set x_park = printer.toolhead.axis_maximum.x|float - 5.0 %}
#   {% set y_park = printer.toolhead.axis_maximum.y|float - 5.0 %}
#   # z position is 10 mm above the print
#   {% set z_park_lift = 10.0 %}
#   # validate the lift position
#   {% set max_z = printer.toolhead.axis_maximum.z|float %}
#   {% set act_z = printer.toolhead.position.z|float %}
#   {% if (act_z + z_park_lift) <= max_z %}
#     {% set z_safe = act_z + z_park_lift %}
#   {% else %}
#     {% set z_safe = max_z %}
#   {% endif %}
#   # park the toolhead at the calculated positions (if all axes are homed)
#   {% if "xyz" in printer.toolhead.homed_axes %}
#     # move in absolute coordinates
#     G90
#     G1 Z{z_safe} F2000
#     G1 X{x_park} Y{y_park} F12000
#     {% if printer.gcode_move.absolute_coordinates|lower == 'false' %}
#       G91
#     {% endif %}
#   {% else %}
#     {action_respond_info("Printer is not homed!")}
#   {% endif %}
#
# Tool change macros (T0-T11) macros will call the internal function SMUFF_TOOL_CHANGE with
# the according tool as parameter. Keep in mind, you'll need as many macros as you have tools
# on your SMuFF. Although, it doesn't hurt configuring the max. number of tools, which in
# this case is 12 (0-11).
#
#   [gcode_macro T0]
#   gcode:
#       SMUFF_TOOL_CHANGE T=0
#   ...
#
#   [gcode_macro T11]
#   gcode:
#       SMUFF_TOOL_CHANGE T=11
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

from threading import Thread, Event
from pprint import pformat

VERSION_NUMBER 	= 1.1 				# Module version number (for scripting)
VERSION_DATE 	= "2022/05/19"
VERSION_STRING	= "SMuFF Module V{0} ({1})" # Module version string

WD_TIMEOUT 		= 10.0				# serial watchdog default timeout

FWINFO		= "M115"        		# SMuFF GCode to query firmware info
PERSTATE    = "M155"     			# SMuFF GCode for enabling sending periodical states
OPT_ON 		= " S1"
OPT_OFF		= " S0"
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
AUTOLOAD	= " S1"          		# additional parameter for auto load after tool swap
ANY 		= "ANY"

# Texts used in console response
T_OK 				= "Ok."
T_ON				= "ON"
T_OFF				= "OFF"
T_YES 				= "YES"
T_NO 				= "NO"
T_TRIGGERED 		= "TRIGGERED"
T_NOT_TRIGGERED 	= "NOT " + T_TRIGGERED
T_REMOVED			= "REMOVED"
T_INSERTED			= "INSERTED"
T_OPENED			= "OPENED"
T_CLOSED			= "CLOSED"
T_NO_TOOL 			= "NO TOOL"
T_TO_SPLITTER		= "TO SPLITTER"
T_TO_SELECTOR 		= "TO  SELECTOR"
T_TO_DDE 			= "TO DDE"
T_INVALID_STATE 	= "UNKNOWN"
T_CFG_GCODE_ERR		= "SMuFF requires [{0}] to work, please add it to your config!"
T_CFG_ERR 			= "No serial port defined for SMuFF. Put serial=/dev/serial/xxx into 'smuff.cfg', where xxx is the 'by-id' value of the tty the SMuFF is connected to."
T_NOT_CONN			= "SMuFF is not yet connected. Use SMUFF_CONNECT first and check 'smuff.cfg' for the correct 'serial' setting."
T_SMUFF_ERR 		= "SMuFF responded with error! [{0}]."
T_SMUFF_RESPONSE 	= "SMuFF responded with {0}."
T_NO_PARAM 			= "No parameter specified ({0}='...')."
T_NO_VALUE 			= "No parameter value specified ({0}='...')."
T_FW_INFO 			= "SMuFF: FW-Info:\n{0}."
T_ERR_SERVOPOS 		= "Servo position must be between 0 and 180."
T_CONN_EX 			= "Connecting to SMuFF has thrown an exception:\n\t{0}."
T_CONN 				= "Connected to SMuFF."
T_DISC 				= "Disconnected from SMuFF"
T_DISC_EX 			= "Disconnecting from SMuFF has thrown an exception:\n\t{0}."
T_IS_CONN 			= "SMuFF is connected on {}."
T_ALDY_CONN 		= "SMuFF is already connected."
T_ISNT_CONN 		= "SMuFF is currently not connected."
T_NO_SEL_TOOL		= "SMuFF tool change: Selected tool (T{0}) exceeds existing tools ({1})."
T_SKIP_TOOL 		= "Selected tool (T{0}) is already loaded. Skipping tool change."
T_DUMP_RAW 			= "SMuFF dump raw serial data is {0}"
T_WIPING			= "Wiping nozzle..."
T_CUTTING			= "Cutting filament..."
T_OPENING_LID		= "Opening lid..."
T_CLOSING_LID		= "Closing lid..."
T_POSITIONING		= "Positioning servo {0} to {1} deg."
T_NOT_READY 		= "Busy with other async task, aborting!"
T_STATE_INFO_NC		= """SMuFF Status:
Connected:\t{0}
Port:\t\t{1}"""
T_STATE_INFO		= """{0}
------------------------
Device name:\t{1}
Tool count:\t{2}
------------------------
Active tool:\t{3}
Selector:\t{4}
Feeder:\t\t{5}
Feeder 2:\t{6}
Lid:\t\t{7}
SD-Card:\t{8}
Idle:\t\t{9}
Config changed:\t{10}
Feeder loaded:\t{11}
------------------------
FW-Version:\t{12}
FW-Board:\t{13}
FW-Mode:\t{14}
FW-Options:\t{15}
------------------------
Tool changes:\t{16}
Average duration:\t{17} s\n"""

# Help texts for commands
T_HELP_CONN 		= "Connect to the SMuFF."
T_HELP_DISC			= "Disconnect from the SMuFF."
T_HELP_CONNECTED	= "Show current connection status."
T_HELP_CUT			= "Cut filament."
T_HELP_WIPE			= "Wipe nozzle."
T_HELP_LID_OPEN		= "Open lid servo."
T_HELP_LID_CLOSE	= "Close lid servo."
T_HELP_SET_SERVO	= "Position a servo."
T_HELP_TOOL_CHANGE	= "Change the current tool."
T_HELP_INFO			= "Query the firmware info from SMuFF."
T_HELP_STATUS		= "Query the status from SMuFF."
T_HELP_SEND			= "Send GCode to the SMuFF."
T_HELP_PARAM		= "Send configuration parameters to the SMuFF."
T_HELP_MATERIALS	= "Query the materials configured on the SMuFF."
T_HELP_SWAPS		= "Query the tool swaps configured on the SMuFF."
T_HELP_LIDMAPPINGS	= "Query the lid servo mappings configured on the SMuFF."
T_HELP_LOAD			= "Load filament on active tool on the SMuFF."
T_HELP_UNLOAD		= "Unload filament from active tool on the SMuFF."
T_HELP_HOME			= "Home Selector (and Revolver if configured) on the SMuFF."
T_HELP_MOTORS_OFF	= "Turn stepper motors on the SMuFF off."
T_HELP_CLEAR_JAM	= "Resets the Feeder Jammed flag on the SMuFF."
T_HELP_RESET		= "Resets the SMuFF."
T_HELP_VERSION		= "Query the version of this module."
T_HELP_RESET_AVG	= "Reset tool change average statistics."
T_HELP_DUMP_RAW		= "Prints out raw sent/received data (for debugging only)."


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

# Some keywords sent by the SMuFF
C_BASIC 		= "basic"
C_STEPPERS 		= "steppers"
C_TMC 			= "tmc driver"
C_MATERIALS 	= "materials"
C_SWAPS 		= "tool swaps"
C_SERVOMAPS 	= "servo mapping"
C_FEEDSTATE 	= "feed state"

CFG_BASIC 		= 1
CFG_STEPPERS 	= 2
CFG_TMC			= 3
CFG_SERVOMAPS 	= 4
CFG_MATERIALS	= 5
CFG_SWAPS 		= 6
CFG_FEEDSTATE	= 8

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
P_TOOL_S		= "T"       		# used in SMUFF_TOOL_CHANGE (i.e. T=0)
P_TOOL_L		= "TOOL"       		# used in SMUFF_TOOL_CHANGE (i.e. TOOL=0)
P_SERVO			= "SERVO"   		# used in SMUFF_SET_SERVO (i.e. SERVO=0)
P_ANGLE			= "ANGLE"   		# used in SMUFF_SET_SERVO (i.e. ANGLE=95)
P_GCODE			= "GCODE"   		# used in SMUFF_SEND (i.e. GCODE="M119")
P_PARAM			= "PARAM" 			# used in SMUFF_PARAM (i.e. PARAM="BowdenLen")
P_PARAMVAL		= "VALUE"  			# used in SMUFF_PARAM (i.e. VALUE="620")
P_ENABLE 		= "ENABLE"			# used in SMUFF_DUMP_RAW

# GCode macros called
PRE_TC 			= "PRE_TOOLCHANGE"
POST_TC 		= "POST_TOOLCHANGE"
G_PRE_TC 		= PRE_TC +" T={0}"
G_POST_TC 		= POST_TC +" P={0} T={1}"

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
		self._wdTimeout 		= 0.0 		# watchdog timeout
		self._toolCount         = 0 		# number of tools on the SMuFF
		self.autoConnect		= False		# flag, whether or not to connect at startup
		self._dumpRawData 		= False		# for debugging only
		self._printer 			= config.get_printer()
		self._reactor 			= self._printer.get_reactor()

		try:
			self.pause_resume = self._printer.load_object(config, "pause_resume")
		except config.error:
			raise self._printer.config_error(T_CFG_GCODE_ERR.format("PAUSE_RESUME"))

		self.gcode = self._printer.lookup_object("gcode")

		# register GCodes for SMuFF
		self.gcode.register_command("SMUFF_CONN",           self.cmd_connect,     	T_HELP_CONN)
		self.gcode.register_command("SMUFF_DISC",           self.cmd_disconnect,  	T_HELP_DISC)
		self.gcode.register_command("SMUFF_CONNECTED",      self.cmd_connected,  	T_HELP_CONNECTED)
		self.gcode.register_command("SMUFF_CUT",            self.cmd_cut,         	T_HELP_CUT)
		self.gcode.register_command("SMUFF_WIPE",           self.cmd_wipe,        	T_HELP_WIPE)
		self.gcode.register_command("SMUFF_LID_OPEN",       self.cmd_lid_open,    	T_HELP_LID_OPEN)
		self.gcode.register_command("SMUFF_LID_CLOSE",      self.cmd_lid_close,   	T_HELP_LID_CLOSE)
		self.gcode.register_command("SMUFF_SET_SERVO",      self.cmd_servo_pos,   	T_HELP_SET_SERVO)
		self.gcode.register_command("SMUFF_TOOL_CHANGE",    self.cmd_tool_change, 	T_HELP_TOOL_CHANGE)
		self.gcode.register_command("SMUFF_INFO",           self.cmd_fw_info,     	T_HELP_INFO)
		self.gcode.register_command("SMUFF_STATUS",         self.cmd_get_states,  	T_HELP_STATUS)
		self.gcode.register_command("SMUFF_SEND",           self.cmd_gcode,       	T_HELP_SEND)
		self.gcode.register_command("SMUFF_PARAM",          self.cmd_param,       	T_HELP_PARAM)
		self.gcode.register_command("SMUFF_MATERIALS",      self.cmd_materials,     T_HELP_MATERIALS)
		self.gcode.register_command("SMUFF_SWAPS",      	self.cmd_swaps,     	T_HELP_SWAPS)
		self.gcode.register_command("SMUFF_LIDMAPPINGS",   	self.cmd_lidmappings,   T_HELP_LIDMAPPINGS)
		self.gcode.register_command("SMUFF_LOAD",   		self.cmd_load,   		T_HELP_LOAD)
		self.gcode.register_command("SMUFF_UNLOAD",   		self.cmd_unload,   		T_HELP_UNLOAD)
		self.gcode.register_command("SMUFF_HOME",   		self.cmd_home,   		T_HELP_HOME)
		self.gcode.register_command("SMUFF_MOTORS_OFF", 	self.cmd_motors_off, 	T_HELP_MOTORS_OFF)
		self.gcode.register_command("SMUFF_CLEAR_JAM",		self.cmd_clear_jam, 	T_HELP_CLEAR_JAM)
		self.gcode.register_command("SMUFF_RESET",			self.cmd_reset, 		T_HELP_RESET)
		self.gcode.register_command("SMUFF_VERSION",		self.cmd_version, 		T_HELP_VERSION)
		self.gcode.register_command("SMUFF_RESET_AVG",		self.cmd_reset_avg, 	T_HELP_RESET_AVG)
		self.gcode.register_command("SMUFF_DUMP_RAW",		self.cmd_dump_raw, 		T_HELP_DUMP_RAW)
		self.gcode.register_command("SMUFF_TEST",			self.cmd_test, 			"")

		# get configuration
		self._serialPort = config.get("serial")
		if not self._serialPort:
			raise config.error(T_CFG_ERR)
		self._baudrate		= config.getint("baudrate", default=115200)
		self._timeout		= config.getfloat("serialTimeout", default=5.0)
		self._cmdTimeout	= config.getfloat("commandTimeout", default=20.0)
		self._tcTimeout		= config.getfloat("toolchangeTimeout", default=90.0)
		self.autoConnect	= config.get("autoConnectSerial", default=T_YES).upper() == T_YES
		self._autoLoad		= config.get("autoLoad", default=T_YES).upper() == T_YES
		self._hasCutter		= config.get("hasCutter", default=T_YES).upper() == T_YES 		# will be eventually overwritten by the SMuFF config
		self._hasWiper 		= config.get("hasWiper", default=T_NO).upper() == T_YES
		self._dumpRawData 	= config.get("debug", default=T_NO).upper() == T_YES
		self._reset()

		# register event handlers
		self._printer.register_event_handler("klippy:disconnect", self.event_disconnect)
		self._printer.register_event_handler("klippy:connect", self.event_connect)
		self._printer.register_event_handler("klippy:ready", self.event_ready)

		#set initial watchdog timeout
		self._wdTimeout = WD_TIMEOUT * 2	# default serial watchdog timeout

	def _reset(self):
		self._log.info("Resetting module")
		self._fwInfo 			= "?"		# SMuFFs firmware info
		self._curTool 			= "T-1"		# the current tool
		self._preTool 			= "T-1"		# the previous tool
		self._pendingTool 		= -1		# the tool on a pending tool change
		self._selector 			= False		# status of the Selector endstop
		self._revolver 			= False		# status of the Revolver endstop
		self._feeder 			= False		# status of the Feeder endstop
		self._feeder2			= False		# status of the 2nd Feeder endstop
		self._isBusy			= False		# flag set when SMuFF signals "Busy"
		self._isError			= False		# flag set when SMuFF signals "Error"
		self._response			= None		# the response string from SMuFF
		self._waitRequested		= False 	# set when SMuFF requested a "Wait" (in case of jams or similar)
		self._abortRequested	= False		# set when SMuFF requested a "Abort"
		self._lastSerialEvent	= 0 		# last time (in millis) a serial receive took place
		self._isProcessing		= False		# set when SMuFF is supposed to be busy
		self._isReconnect 	    = False		# set when trying to re-establish serial connection
		self._isConnected       = False     # set after connection has been established
		self._autoLoad          = True      # set to load new filament automatically after swapping tools
		self._serEvent			= Event()	# event raised when a valid response has been received
		self._serWdEvent		= Event()	# event raised when status data has been received
		self._sdcard            = False     # set to True when SD-Card on SMuFF was removed
		self._cfgChange         = False     # set to True when SMuFF configuration has changed
		self._lid               = False     # set to True when Lid on SMuFF is open
		self._isIdle            = False     # set to True when SMuFF is idle
		self._usesTmc           = False     # set to True when SMuFF uses TMC drivers
		self._tmcWarning        = False     # set to True when TMC drivers on SMuFF report warnings
		self._lastResponse     	= []		# last response SMuFF has sent (multiline)
		self._device 			= "" 		# current name of the SMuFF
		self._stopSerial 		= False		# flag set when the serial reader / connector / watchdog need to be discarded
		if self._serial:					# pySerial instance
			self._close_serial()
		self._sreader 			= None		# serial reader thread instance
		self._sconnector		= None		# serial connector thread instance
		self._swatchdog			= None		# serial watchdog thread instance
		self._jsonCat 			= None		# category of the last JSON string received
		self._materials 		= []		# Two dimensional array of materials received from the SMuFF after SMUFF_MATERIALS
		self._swaps 			= []		# One dimensional array of tool swaps received from the SMuFF after SMUFF_SWAPS
		self._servoMaps			= [] 		# One dimensional array of servo mappings received from the SMuFF after SMUFF_LIDMAPPINGS
		self._feedStates		= [] 		# One dimensional array the feed state for each tool
		self._fwVersion 		= None		# firmware version on the SMuFF (i.e. "V3.10D")
		self._fwBoard 			= None		# board the SMuFF is running on (i.e. "SKR E3-DIP V1.1")
		self._fwMode 			= None		# firmware mode on the SMuFF (i.e. "SMUFF" or "PMMU2")
		self._fwOptions 		= None		# firmware options installed on the SMUFF (i.e "TMC|NEOPIXELS|DDE|...")
		self._stCount 			= 0 		# counter for states recevied
		self._tcCount 			= 0			# number of tool changes in total (since reset)
		self._tcStartTime 		= 0			# time for tool change duration measurement
		self._initStartTime		= 0			# time for _init_SMuFF timeout checking
		self._durationTotal 	= 0.0		# duration of all tool changes (for calculating average)
		self._okTimer 			= None		# (reactor) timer waiting for OK response
		self._initTimer			= None		# (reactor) timer for _init_SMuFF
		self._tcTimer 			= None		# (reactor) timer waiting for toolchange to finish
		self._tcState			= 0			# tool change state
		self._initState			= 0			# state for _init_SMuFF
		self._lastCmdSent		= None		# GCode of the last command sent to SMuFF
		self._lastCmdDone		= False		# flag if the last command sent has got a response
		self._loadState 		= 0			# load state of the current tool
		self._isDDE 			= False		# flag whether the SMuFF is configured for DDE
		self._hasSplitter 		= False		# flag whether the SMuFF is configured for the Splitter option

    #
    # Klippy disconnect handler
    #
	def event_disconnect(self):
		# make sure to clean up ressources (i.e. serial reader thread) otherwise
		# it'll interfere with the new instance after firmware restart
		if self._serial:
			self._log.info("Klippy has disconnected, closing serial communication to SMuFF")
			self._close_serial()

    #
    # Klippy connect handler
    #
	def event_connect(self):
		self._log.info("Klippy has connected")

    #
    # Klippy ready handler
    #
	def event_ready(self):
		self._log.info("Klippy is ready")
		if not PRE_TC in self.gcode.ready_gcode_handlers:
			raise self._printer.config_error(T_CFG_GCODE_ERR.format("gcode_macro '{0}'".format(PRE_TC)))
		else:
			self._log.info("gcode_macro '{0}' check OK".format(PRE_TC))
		if not POST_TC in self.gcode.ready_gcode_handlers:
			raise self._printer.config_error(T_CFG_GCODE_ERR.format("gcode_macro '{0}'".format(POST_TC)))
		else:
			self._log.info("gcode_macro '{0}' check OK".format(POST_TC))


    #
    # SMUFF_CONN
    #
	def cmd_connect(self, gcmd=None, autoConnect=None):
		if self._isConnected:
			self.gcode.respond_info(T_ALDY_CONN)
			return True
		try:
			self._connect_SMuFF(gcmd)
			if autoConnect and autoConnect ==  True:
				return True
		except Exception as err:
			self.gcode.respond_info(T_CONN_EX.format(err))
			return False

		if self._isConnected:
			self.gcode.respond_info(T_CONN)
			return True
		return False

    #
    # SMUFF_DISC
    #
	def cmd_disconnect(self, gcmd=None):
		try:
			self._close_serial()
			self.gcode.respond_info(T_DISC)
		except Exception as err:
			self.gcode.respond_info(T_DISC_EX.format(err))

		self._serial = None

    #
    # SMUFF_CONNECTED
    #
	def cmd_connected(self, gcmd):
		if self._isConnected:
			self.gcode.respond_info(T_IS_CONN.format(self._serialPort))
		else:
			self.gcode.respond_info(T_ISNT_CONN)

    #
    # SMUFF_CUT
    #
	def cmd_cut(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self.gcode.respond_info(T_CUTTING)
		self._send_SMuFF(CUT)

    #
    # SMUFF_WIPE
    #
	def cmd_wipe(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self.gcode.respond_info(T_WIPING)
		self._send_SMuFF(WIPE)

    #
    # SMUFF_LID_OPEN
    #
	def cmd_lid_open(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self.gcode.respond_info(T_OPENING_LID)
		self._send_SMuFF(LIDOPEN)

    #
    # SMUFF_LID_CLOSE
    #
	def cmd_lid_close(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self.gcode.respond_info(T_CLOSING_LID)
		self._send_SMuFF(LIDCLOSE)

    #
    # SMUFF_SET_SERVO
    #
	def cmd_servo_pos(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		servo = gcmd.get_int(P_SERVO, default=1) 	# Lid servo by default
		pos = gcmd.get_int(P_ANGLE, default=90)
		if pos < 0 or pos > 180:
			gcmd.respond_info(T_ERR_SERVOPOS)
			return
		self.gcode.respond_info(T_POSITIONING.format(servo, pos))
		self._send_SMuFF(SETSERVO.format(servo, pos))

    #
    # SMUFF_TOOL_CHANGE
    #
	def cmd_tool_change(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		if not self._tcTimer is None:
			self.gcode.respond_info(T_NOT_READY)
			return
		# retrieve current and pending tool
		self._activeTool = self._parse_tool_number(self._curTool)
		self._pendingTool = gcmd.get_int(P_TOOL_S, default=-1)
		if self._pendingTool == -1:
			self._pendingTool = gcmd.get_int(P_TOOL_L, default=-1)
			if self._pendingTool == -1:
				self.gcode.respond_info(T_NO_PARAM.format(P_TOOL_L))
				return
		# check pending tool for validity
		if self._pendingTool > self._toolCount:
			self.gcode.respond_info(T_NO_SEL_TOOL.format(self._pendingTool, self._toolCount))
			self._pendingTool = -1
			return

		# no tool change needed as we already have the right tool selected
		if self._activeTool == self._pendingTool:
			self._log.info("No tool change needed, skipping...")
			self.gcode.respond_info(T_SKIP_TOOL.format(self._pendingTool))
		else:
			# need to change tool, setup async function
			if self._tcTimer is None:
				self._tcState = 1
				self._tcTimer = self._reactor.register_timer(self._tool_change, self._reactor.NOW)

    #
    # SMUFF_INFO
    #
	def cmd_fw_info(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self.gcode.respond_info(T_FW_INFO.format(self._fwInfo))

    #
    # SMUFF_STATUS
    #
	def cmd_get_states(self, gcmd=None):
		connStat = T_STATE_INFO_NC.format(
			T_YES if self._isConnected else T_NO,
			self._serialPort)
		if self._isConnected:
			durationAvg =  (self._durationTotal / self._tcCount) if self._durationTotal > 0 and self._tcCount > 0 else 0
			loadState = {
				-1: T_NO_TOOL,
					0: T_NO,
					1: T_TO_SPLITTER if self._hasSplitter else T_TO_SELECTOR,
					2: T_YES,
					3: T_TO_DDE
			}
			loaded = loadState.get(self._loadState, T_INVALID_STATE)

			self.gcode.respond_info(T_STATE_INFO.format(
				connStat,
				self._device,
				self._toolCount,
				self._curTool,
				T_TRIGGERED if self._selector else T_NOT_TRIGGERED,
				T_TRIGGERED if self._feeder else T_NOT_TRIGGERED,
				T_TRIGGERED if self._feeder2 else T_NOT_TRIGGERED,
				T_CLOSED if self._lid else T_OPENED,
				T_REMOVED if self._sdcard else T_INSERTED,
				T_YES if self._isIdle else T_NO,
				T_YES if self._cfgChange else T_NO,
				loaded,
				self._fwVersion,
				self._fwBoard,
				self._fwMode,
				self._fwOptions,
				self._tcCount,
				durationAvg))
		else:
			self.gcode.respond_info(connStat)
    #
    # SMUFF_SEND
    #
	def cmd_gcode(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		gcode = gcmd.get(P_GCODE)
		if not gcode:
			gcmd.respond_info(T_NO_PARAM.format(P_GCODE))
			return
		if gcode.upper() == RESET:
			self._serWdEvent.set()
			self._wdTimeout = WD_TIMEOUT*2
			self._send_SMuFF(gcode)
		else:
			response = self._send_SMuFF_and_wait(gcode)
			if response:
				gcmd.respond_info(T_SMUFF_RESPONSE.format(response))

    #
    # SMUFF_PARAM
    #
	def cmd_param(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		param = gcmd.get(P_PARAM)
		paramVal = gcmd.get(P_PARAMVAL)
		if not param:
			gcmd.respond_info(T_NO_PARAM.format(P_PARAM))
			return
		if not paramVal:
			gcmd.respond_info(T_NO_VALUE.format(P_PARAMVAL))
			return
		response = self._send_SMuFF_and_wait(SETPARAM.format(param, paramVal))
		if self._isError:
			gcmd.respond_info(T_SMUFF_ERR.format(response))

    #
    # SMUFF_MATERIALS
    #
	def cmd_materials(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(GETCONFIG.format(CFG_MATERIALS))

    #
    # SMUFF_SWAPS
    #
	def cmd_swaps(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(GETCONFIG.format(CFG_SWAPS))

    #
    # SMUFF_LIDMAPPINGS
    #
	def cmd_lidmappings(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(GETCONFIG.format(CFG_SERVOMAPS))

    #
    # SMUFF_LOAD
    #
	def cmd_load(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		if not self._okTimer is None:
			self.gcode.respond_info(T_NOT_READY)
			return
		activeTool = self._parse_tool_number(self._curTool)
		if activeTool != -1:
			self._lastCmdSent = LOAD
			self._send_SMuFF(LOAD)
			self._lastCmdDone = False
			self._okTimer = self._reactor.register_timer(self._wait_for_ok, self._reactor.NOW + 5.0)

    #
    # SMUFF_UNLOAD
    #
	def cmd_unload(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		if not self._okTimer is None:
			self.gcode.respond_info(T_NOT_READY)
			return
		activeTool = self._parse_tool_number(self._curTool)
		if activeTool != -1:
			self._lastCmdSent = UNLOAD
			self._send_SMuFF(UNLOAD)
			self._lastCmdDone = False
			self._okTimer = self._reactor.register_timer(self._wait_for_ok, self._reactor.NOW + 5.0)

    #
    # SMUFF_HOME
    #
	def cmd_home(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(HOME)

    #
    # SMUFF_MOTORS_OFF
    #
	def cmd_motors_off(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(MOTORSOFF)

    #
    # SMUFF_CLEAR_JAM
    #
	def cmd_clear_jam(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(UNJAM)

    #
    # SMUFF_RESET
    #
	def cmd_reset(self, gcmd=None):
		if not self._isConnected:
			self.gcode.respond_info(T_NOT_CONN)
			return
		self._send_SMuFF(RESET)

    #
    # SMUFF_VERSION
    #
	def cmd_version(self, gcmd=None):
		self.gcode.respond_info(VERSION_STRING.format(VERSION_NUMBER, VERSION_DATE))

    #
    # SMUFF_RESET_AVG
    #
	def cmd_reset_avg(self, gcmd=None):
		self._tcCount = 0
		self._durationTotal = 0.0
		self.gcode.respond_info(T_OK)

    #
    # SMUFF_DUMP_RAW
    #
	def cmd_dump_raw(self, gcmd=None):
		self._dumpRawData = not self._dumpRawData
		self.gcode.respond_info(T_DUMP_RAW.format(T_ON if self._dumpRawData else T_OFF))

    #
    # SMUFF_TEST
    #
	def cmd_test(self, gcmd=None):
		param = gcmd.get("P")
		if param == "P":
			self.gcode.run_script_from_command(G_PRE_TC.format(self._pendingTool))
		elif param == "R":
			self.gcode.run_script_from_command(G_POST_TC.format(self._pendingTool, self._pendingTool))
		self.gcode.respond_info(T_OK)

	#
	# Set status values to be used within Klipper (scripts, GCode)
	#
	def get_status(self, eventtime=None):
		#self._log.info("get_status being called. M:{0} S:{1} ")
		values = {
			"tools":   		self._toolCount,
			"activetool":   self._parse_tool_number(self._curTool),
			"pendingtool":  self._pendingTool,
			"selector":     self._selector,
			"revolver":     self._revolver,
			"feeder":       self._feeder,
			"feeder2":      self._feeder2,
			"fwinfo":       self._fwInfo,
			"isbusy":       self._isBusy,
			"iserror":      self._isError,
			"isprocessing": self._isProcessing,
			"isconnected":	self._isConnected,
			"isidle": 		self._isIdle,
			"sdstate": 		self._sdcard,
			"lidstate": 	self._lid,
			"hascutter":	self._hasCutter,
			"haswiper":		self._hasWiper,
			"materials": 	self._materials,
			"swaps":		self._swaps,
			"lidmappings":	self._servoMaps,
			"device": 		self._device,
			"version": 		VERSION_NUMBER,
			"fwversion":	self._fwVersion,
			"fwmode":		self._fwMode,
			"fwoptions":	self._fwOptions,
			"loadstate":	self._loadState,
			"isdde":		self._isDDE,
			"hassplitter":	self._hasSplitter
		}
		return values


	#------------------------------------------------------------------------------
	# Async helper functions
	#------------------------------------------------------------------------------

	#
	# Async tool change (to satisfy Klipper/Klippy)
	#
	# If tasks run for a long time (such as the tool change), not using
	# the reactor timer will cause the main process (Klippy) to be blocked
	# and hence some processes in Klippy will come out of sync.
	# This may mess up the internal handlers and result in some really
	# strange messages, such as "SD Busy" or shutdown Klipper while
	# printing.
	# The reactor timer uses a callback and a event time and will
	# call the method as long as the timer isn't discarded. Returning
	# the current eventtime with an offset will determine when the next
	# call is going to take place.
	#
	# This method uses an internal state machine, so various steps
	# can be split up and run with various timings. Each state will call
	# the next one as it finishes. State 3 is the one waiting for the SMuFF
	# to finish the tool change and hence it's timing is set to every 2 seconds.
	#
	def _tool_change(self, eventtime):

		if self._dumpRawData:
			self._log.info("Tool change state = {0}".format(self._tcState))

		# state 1: run PRE_TOOLCHANGE macro
		if self._tcState == 1:
			self._tcCount +=1
			self._tcStartTime = self._nowMS()
			self._preTool = self._curTool

			if self._is_printing():
				# run PRE_TOOLCHANGE gcode macro
				self._log.info("Executing script {0}".format(G_PRE_TC.format(self._pendingTool)))
				try:
					self.gcode.run_script_from_command(G_PRE_TC.format(self._pendingTool))
					self._tcState = 2
				except self.gcode.error as err:
					self._log.error("Script {0} has thrown an exception:\n\t{1}".format(PRE_TC, err))
					self._tcState = 0
			else:
				self._tcState = 2
			return eventtime + 0.1

		# state 2: send tool change command to SMuFF
		elif self._tcState == 2:
			self._lastCmdDone = False
			# do the tool change on SMuFF
			self._log.info("Changing tool from T{0} to T{1}".format(self._activeTool, self._pendingTool))
			self._lastCmdSent = TOOL + str(self._pendingTool)
			self._send_SMuFF(self._lastCmdSent + (AUTOLOAD if self._autoLoad else ""))
			self._tcState = 3
			return eventtime + 5.0

		# state 3: wait for response from SMuFF
		elif self._tcState == 3:
			if self._lastCmdDone:
				if self._isError:
					self._log.info("Tool change done, got ERROR response - skipping RESUME")
					self._tcState = 6
				else:
					self._log.info("Tool change done, got OK response")
					self._tcState = 4
				return eventtime + 0.1
			else:
				watchdog = (self._nowMS()-self._tcStartTime)/1000
				# task already running longer than expected, interrupt it
				# otherwise it'd run infinitly
				if watchdog > self._tcTimeout:
					self._log.error("Timed out while waiting for a response. Try increasing the tool change timeout (={0} sec.).".format(self._tcTimeout))
					self._tcState = 6
				return eventtime + 1.0

		# state 4: query feed state from SMuFF
		elif self._tcState == 4:
			self._lastCmdSent = GETCONFIG.format(CFG_FEEDSTATE)
			self._send_SMuFF(self._lastCmdSent)
			self._tcState = 5
			return eventtime + 0.2

		# state 5: run POST_TOOLCHANGE macro
		elif self._tcState == 5:
			if self._is_print_paused():
				prevTool = self._parse_tool_number(self._preTool)
				# run POST_TOOLCHANGE gcode macro
				self._log.info("Executing script {0}".format(G_POST_TC.format(prevTool, self._activeTool)))
				try:
					self.gcode.run_script_from_command(G_POST_TC.format(prevTool, self._activeTool))
				except self.gcode.error as err:
					self._log.error("Script {0} has thrown an exception:\n\t{1}".format(POST_TC, err))
			self._tcState = 6
			return eventtime + 0.1

		# state 6: calculate duration and end
		elif self._tcState == 6:
			duration = (self._nowMS()-self._tcStartTime)/1000
			self._durationTotal += duration
			self._log.info("Tool change took {0} seconds. Average is {1} seconds".format(duration, self._durationTotal / self._tcCount))
			self._tcState = 0
			return eventtime + 0.1

		# any other state: discard the timer
		else:
			self._reactor.unregister_timer(self._tcTimer)
			self._tcTimer = None

	#
	# Async load / unload handler
	#
	def _wait_for_ok(self, eventtime):
		if self._lastCmdDone:
			if self._isError:
				self._log.info("_wait_for_ok done got ERROR response")
			else:
				self._log.info("_wait_for_ok done, got OK response")
			self._reactor.unregister_timer(self._okTimer)
			self._okTimer = None
		else:
			self._log.info("waiting for ok...")
			return eventtime + 2.0

	#
	# Async basic init
	#
	def _async_init(self):
		if self._dumpRawData:
			self._log.info("_async_init: state {0} processing: {1}".format(self._initState, self._isProcessing))
		if self._initState == 1:
			# query some basic configuration settings
			if self._isProcessing == False:
				self._send_SMuFF(GETCONFIG.format(CFG_BASIC))
		elif self._initState == 2:
			# query materials configuration
			if self._isProcessing == False:
				self._send_SMuFF(GETCONFIG.format(CFG_MATERIALS))
		elif self._initState == 3:
			# request firmware info from SMuFF
			if self._isProcessing == False:
				self._send_SMuFF(FWINFO)
		elif self._initState == 4:
			# query tool swap configuration settings
			if self._isProcessing == False:
				self._send_SMuFF(GETCONFIG.format(CFG_SWAPS))
		elif self._initState == 5:
			# query some lid servo mapping settings
			if self._isProcessing == False:
				self._send_SMuFF(GETCONFIG.format(CFG_SERVOMAPS))
		else:
			self._initState = 0


	#
	# helper functions
	#
	def _is_printing(self):
		idle_timeout = self._printer.lookup_object("idle_timeout")
		return idle_timeout.state == ST_PRINTING

	def _is_print_paused(self):
		state = self._printer.lookup_object("pause_resume")
		return state.is_paused


	#------------------------------------------------------------------------------
	# SMuFF core functions
	#------------------------------------------------------------------------------

	#
	# Connects to the SMuFF via the configured serial interface (/dev/ttySMuFF by default)
	#
	def _connect_SMuFF(self, gcmd=None):
		self._isConnected = False

		try:
			self._open_serial()
			if self._serial and self._serial.is_open:
				self._isConnected = True
				self._init_SMuFF() 	# query firmware info and current settings from the SMuFF
			else:
				self._log.info("Opening serial {0} for SMuFF has failed".format(self._serialPort))
				return
		except Exception as err:
			self._log.error("Connecting to SMuFF has thrown an exception:\n\t{0}".format(err))

	#
	# Opens the serial port for the communication with the SMuFF
	#
	def _open_serial(self):
		try:
			self._log.info("Opening serial port '{0}'".format(self._serialPort))
			self._serial = serial.Serial(self._serialPort, self._baudrate, timeout=self._timeout, write_timeout=0)
			if self._serial and self._serial.is_open:
				self._log.info("Serial port opened")
				self._stopSerial = False
				try:
					# set up a separate task for reading the incoming SMuFF messages
					self._sreader = Thread(target=self._serial_reader, name="TReader")
					self._sreader.daemon = True
					self._sreader.start()
					self._log.info("Serial reader thread running... ({0})".format(self._sreader))
				except:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
					self._log.error("Unable to start serial reader thread: ".join(tb))
				self._start_watchdog()
		except (OSError, serial.SerialException):
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Can't open serial port '{0}'!\n\t{1}".format(self._serialPort, tb))

	#
	# Closes the serial port and cleans up resources
	#
	def _close_serial(self):
		if not self._serial:
			self._log.info("Serial wasn't initialized, nothing to do here")
			return
		self._stopSerial = True
		# stop threads
		try:
			if self._sconnector and self._sconnector.is_alive:
				self._sconnector.join()
			else:
				self._log.error("Serial connector isn't alive")
		except Exception as err:
			self._log.error("Unable to shut down serial connector thread:\n\t{0}".format(err))
		try:
			self._serWdEvent.set()
			if self._swatchdog and self._swatchdog.is_alive:
				self._swatchdog.join()
			else:
				self._log.error("Serial watchdog isn't alive")
		except Exception as err:
			self._log.error("Unable to shut down serial watchdog thread:\n\t{0}".format(err))
		try:
			if self._sreader and self._sreader.is_alive:
				self._sreader.join()
			else:
				self._log.error("Serial reader isn't alive")
		except Exception as err:
			self._log.error("Unable to shut down serial reader thread:\n\t{0}".format(err))

		# discard reader, connector and watchdog threads
		del(self._sreader)
		del(self._sconnector)
		del(self._swatchdog)
		self._sreader = None
		self._sconnector = None
		self._swatchdog = None
		# close the serial port
		try:
			self._serial.close()
			if self._serial.is_open == False:
				self._log.info("Serial port '{0}' closed".format(self._serial.port))
			else:
				self._log.error("Closing serial port '{0}' has failed".format(self._serial.port))
			del(self._serial)
			self._serial = None
			self._isConnected = False
		except (OSError, serial.SerialException):
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Can't close serial port {0}!\n\t{1}".format(self._serialPort, tb))

	#
	# Serial reader thread
	#
	def _serial_reader(self):
		self._log.info("Entering serial reader thread")
		# this loop basically runs forever, unless _stopSerial is set or the
		# serial port gets closed
		while self._stopSerial == False:
			if self._serial and self._serial.is_open:
				try:
					b = self._serial.in_waiting
					if b > 0:
						try:
							data = self._serial.readline().decode("ascii")	# read to EOL
							self._parse_serial_data(data)
						except UnicodeDecodeError as err:
							self._log.error("Serial reader has thrown an exception:\n\t{0}\n\tData: [{1}]".format(err, data))
							self._serial.reset_input_buffer()
						except:
							exc_type, exc_value, exc_traceback = sys.exc_info()
							tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
							self._log.error("Serial reader error: ".join(tb))
				except serial.SerialException as err:
					self._log.error("Serial reader has thrown an exception:\n\t{0}".format(err))
					self._serEvent.set()
				except serial.SerialTimeoutException as err:
					self._log.error("Serial reader has timed out:\n\t{0}".format(err))
					self._serEvent.set()
			else:
				self._log.error("Serial port {0} has been closed".format(self._serial.port))
				self._serEvent.set()
				break

		self._log.error("Shutting down serial reader")

	#
	# Method which starts _serial_connector() in the background.
	#
	def start_connector(self):
		try:
			# set up a separate task for connecting to the SMuFF
			self._sconnector = Thread(target=self._serial_connector, name="TConnector")
			self._sconnector.daemon=True
			self._sconnector.start()
			self._log.info("Serial connector thread running... ({0})".format(self._sconnector))
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Unable to start serial connector thread: ".join(tb))

	#
	# Serial connector thread
	# This part runs in a thread in order not to block Klipper during start up
	#
	def _serial_connector(self):
		self._log.info("Entering serial connector thread")
		time.sleep(3)

		while 1:
			if self._stopSerial == True:
				break
			if self.cmd_connect(autoConnect=True) == True:
				break
			time.sleep(1)
			self._log.info("Serial connector looping...")

		# as soon as the connection has been established, cancel the connector thread
		self._log.info("Shutting down serial connector")
		self._sconnector = None

	#
	# Method which starts _serial_watchdog() in the background.
	#
	def _start_watchdog(self):
		try:
			# set up a separate task for connecting to the SMuFF
			self._swatchdog = Thread(target=self._serial_watchdog, name="TWatchdog")
			self._swatchdog.daemon=True
			self._swatchdog.start()
			self._log.info("Serial watchdog thread running... ({0})".format(self._swatchdog))
		except:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
			self._log.error("Unable to start serial watchdog thread: ".join(tb))

	#
	# Serial watchdog thread
	#
	def _serial_watchdog(self):
		self._log.info("Entering serial watchdog thread")

		while self._stopSerial == False:
			if self._serial.is_open == False:
				break
			self._serWdEvent.clear()
			is_set = self._serWdEvent.wait(self._wdTimeout)
			if self._stopSerial:
				break
			if is_set == False:
				self._log.info("Serial watchdog timed out... (={0} sec.)".format(self._wdTimeout))
				#reconnect = Thread(target=self._reconnect_SMuFF, name="TReconnect").start()
				#break

		self._log.info("Shutting down serial watchdog")

    #
	# Tries to reconnect serial port to SMuFF
    #
	def _reconnect_SMuFF(self):
		if self._sconnector:
			self._log.info("Connector thread running, aborting reconnect request...")
			return
		self._close_serial()
		self._isReconnect = True
		self._log.info("Attempting a reconnect...")
		self._connect_SMuFF()
		self._isReconnect = False
		if self._isConnected == False:
			self._log.info("Still not connected, starting connector")
			self.start_connector()
		else:
			if self._serial.is_open:
				if self._send_SMuFF_and_wait(FWINFO) == None:
					self._log.info("No valid response, starting connector")


    #
	# Sends data to SMuFF
    #
	def _send_SMuFF(self, data):
		self._set_busy(False)		# reset busy and
		self._set_error(False)		# error flags

		if self._lastCmdSent == None:
			elements = data.split(" ", 1)
			if len(elements):
				self._lastCmdSent = elements[0]
			else:
				self._lastCmdSent = elements

		if self._serial and self._serial.is_open:
			try:
				b = bytearray(len(data)+2)
				b = "{0}\n".format(data).encode("ascii")
				n = self._serial.write(b)
				if self._dumpRawData:
					self._log.info("Sent {1} bytes: [{0}]".format(b, n))
				return True
			except (OSError, serial.SerialException) as err:
				self._log.error("Unable to send command '{0}:\n\t' to SMuFF".format(data, err))
				return False
		else:
			self._log.error("Serial port is closed, can't send data")
			return False

    #
	# Sends data to SMuFF and will wait for a response (which in most cases is 'ok')
    #
	def _send_SMuFF_and_wait(self, data):

		if data.startswith(TOOL):
			timeout = self._tcTimeout 	# wait max. 90 seconds for a response while swapping tools
			tmName = "tool change"
		else:
			timeout = self._cmdTimeout	# wait max. 25 seconds for other operations
			tmName = "command"
		self._wdTimeout = timeout
		done = False
		result = None

		if self._send_SMuFF(data) == False:
			self._log.error("Failed to send command to SMuFF, aborting 'send_SMuFF_and_wait'")
			return None
		self._set_processing(True)	# SMuFF is currently doing something

		while not done:
			self._serEvent.clear()
			is_set = self._serEvent.wait(timeout)
			if is_set == True:
				self._log.info("To [{0}] SMuFF says [{1}]  {2}".format(data, self._response, "(Error reported)" if self._isError else "(Ok)"))
				result = self._response
				if self._response == None or self._isError:
					done = True
				elif not self._response.startswith(R_ECHO):
					done = True

				self._response = None
			else:
				self._log.info("Timed out while waiting for a response on cmd '{0}'. Try increasing the {1} timeout (={2} sec.).".format(data, tmName, timeout))
				if self._isBusy == False:
					done = True
					self._set_processing(False)

		self._set_processing(False)	# SMuFF is not supposed to do anything
		self._wdTimeout = WD_TIMEOUT
		return result

	#
	# Initializes data of this module by requesting runtime setting from the SMuFF
	#
	def _init_SMuFF(self):
		self._log.info("Sending SMuFF init...")
		# turn on sending of periodical states
		self._send_SMuFF(PERSTATE + OPT_ON)

	#
	# set/reset processing flag
	#
	def _set_processing(self, processing):
		self._isProcessing = processing

	#
	# set/reset busy flag
	#
	def _set_busy(self, busy):
		self._isBusy = busy

	#
	# set/reset error flag
	#
	def _set_error(self, error):
		self._isError = error

	#
	# set last response received (i.e. everything below the GCode and above the "ok\n")
	#
	def _set_response(self, response):
		if not response == None:
			self._response = response.rstrip("\n")
		else:
			self._response = ""
		self._lastResponse = []

	#
	# Dump string s as a hex string (for debugging only)
	#
	def _hex_dump(self, s):
		self._log.info(":".join("{:02x}".format(ord(c)) for c in s))

    #
    # Parses a JSON response sent by the SMuFF (used for retrieving SMuFF settings)
    #
	def _parse_json(self, data, category):
		if category == None or data == None:
			return
		if self._dumpRawData:
			self._log.info("Parse JSON (category '{1}'):\n\t[{0}]".format(data, category))

		if data:
			resp = ""
			try:
				cfg = json.loads(data)
				if cfg == None:
					return
				# basic configuration
				if category == C_BASIC:
					self._device 		= cfg["Device"]
					self._toolCount 	= cfg["Tools"]
					self._hasCutter 	= cfg["UseCutter"]
					self._hasSplitter 	= cfg["UseSplitter"]
					self._isDDE 		= cfg["UseDDE"]

				# stepper configuration
				if category == C_STEPPERS:
					pass

				# TMC driver configuration
				if category == C_TMC:
					pass

				# materials configuration
				if category == C_MATERIALS:
					try:
						self._materials = []
						for i in range(self._toolCount):
							t = "T"+str(i)
							material = [ cfg[t]["Material"], cfg[t]["Color"], cfg[t]["PFactor"] ]
							self._materials.append(material)
							#resp += "Tool {0} is '{2} {1}' with a purge factor of {3}%\n".format(i, material[0], material[1], material[2])
					except Exception as err:
						self._log.error("Parsing materials has thrown an exception:\n\t{0}".format(err))

				# tool swapping configuration
				if category == C_SWAPS:
					try:
						self._swaps = []
						for i in range(self._toolCount):
							t = "T"+str(i)
							swap = cfg[t]
							self._swaps.append(swap)
							#resp += "Tool {0} is assigned to tray {1}\n".format(i, swap)
					except Exception as err:
						self._log.error("Parsing tool swaps has thrown an exception:\n\t{0}".format(err))

				# servo mapping configuration
				if category == C_SERVOMAPS:
					try:
						self._servoMaps = []
						for i in range(self._toolCount):
							t = "T"+str(i)
							servoMap = cfg[t]["Close"]
							self._servoMaps.append(servoMap)
							#resp += "Tool {0} closed @ {1} deg.\n".format(i, servoMap)
					except Exception as err:
						self._log.error("Parsing lid mappings has thrown an exception:\n\t{0}".format(err))

				# feeder states
				if category == C_FEEDSTATE:
					try:
						self._feedStates = []
						for i in range(self._toolCount):
							t = "T"+str(i)
							feedState = cfg[t]
							self._feedStates.append(feedState)
							#resp += "Tool load state {0}\n".format(i, feedState)
					except Exception as err:
						self._log.error("Parsing feed states has thrown an exception:\n\t{0}".format(err))

				if len(resp):
					try:
						self.gcode.respond_info(resp)
					except Exception as err:
						self._log.error("Sending response tp Klipper has thrown an exception:\n\t{0}".format(err))

			except Exception as err:
				self._log.error("Parse JSON for category {1} has thrown an exception:\n\t{0}\n\t[{1}]".format(err, self._jsonCat, data))

    #
    # Parses the states periodically sent by the SMuFF
    #
	def _parse_states(self, states):
		#self._log.info("States received: [" + states + "]")
		if len(states) == 0:
			return False

		# Note: SMuFF sends periodically states in this notation:
		# 	"echo: states: T: T4  S: off  R: off  F: off  F2: off  TMC: -off  SD: off  SC: off  LID: off  I: off  SPL: 0"
		for m in re.findall(r'([A-Z]{1,3}[\d|:]+).(\+?\w+|-?\d+|\-\w+)+',states):
			if   m[0] == "T:":                          # current tool
				self._curTool      	= m[1].strip()
			elif m[0] == "S:":                          # Selector endstop state
				self._selector      = m[1].strip() == T_ON.lower()
			elif m[0] == "R:":                          # Revolver endstop state
				self._revolver      = m[1].strip() == T_ON.lower()
			elif m[0] == "F:":                          # Feeder endstop state
				self._feeder        = m[1].strip() == T_ON.lower()
			elif m[0] == "F2:":                         # DDE-Feeder endstop state
				self._feeder2       = m[1].strip() == T_ON.lower()
			elif m[0] == "SD:":                         # SD-Card state
				self._sdcard        = m[1].strip() == T_ON.lower()
			elif m[0] == "SC:":                         # Settings Changed
				self._cfgChange     = m[1].strip() == T_ON.lower()
			elif m[0] == "LID:":                        # Lid state
				self._lid           = m[1].strip() == T_ON.lower()
			elif m[0] == "I:":                          # Idle state
				self._isIdle        = m[1].strip() == T_ON.lower()
			elif m[0] == "TMC:":                        # TMC option
				v = m[1].strip()
				self._usesTmc = v.startswith("+")
				self._tmcWarning = v[1:] == T_ON.lower()
			elif m[0] == "SPL:":                        # Splitter/Feeder load state
				self._spl = int(m[1].strip())
				if self._curTool == "-1":
					self._loadState = -1					# no tool selected
				else:
					if self._spl == 0:
						self._loadState = 0					# not loaded
					if self._spl == 0x01 or self._spl == 0x10:
						self._loadState = 1					# loaded to Selector or Splitter
					if self._spl == 0x02 or self._spl == 0x20:
						self._loadState = 2					# loaded to Nozzle
					if self._spl == 0x40:
						self._loadState = 3					# loaded to DDE

			#else:
				#	self._log.error("Unknown state: [" + m[0] + "]")
		self._serWdEvent.set()
		self._stCount += 1
		if self._initState > 0:
			self._async_init()
		return True

    #
	# Converts the string 'Tn' into a tool number
    #
	def _parse_tool_number(self, tool):
		if not tool or tool == "":
			return -1
		try:
			#self._log.info("Tool: [{}]".format(tool))
			return int(re.findall(r'[-\d]+', tool)[0])
		except Exception as err:
			self._log.error("Can't parse tool number in {0}:\n\t{1}".format(tool, err))
		return -1

    #
	# Parses the response we've got from the SMuFF
    #
	def _parse_serial_data(self, data):
		if data == None or len(data) == 0 or data == "\n":
			return

		if self._dumpRawData:
			self._log.info("Raw data: [{0}]".format(data.rstrip("\n")))

		self._lastSerialEvent = self._nowMS()
		self._serEvent.clear()

		# after first connect the response from the SMuFF is supposed to be 'start'
		if data.startswith(R_START):
			self._log.info("\"start\" response received")
			self._serEvent.set()
			self._init_SMuFF()
			return

		if data.startswith(PERSTATE):
			if self._dumpRawData:
				self._log.info("Periodical states sending is ON")
			self._initState = 1
			return

		if data.startswith(R_ECHO):
			# don't process any general debug messages
			index = len(R_ECHO)+1
			if data[index:].startswith(R_DEBUG):
				self._log.debug("SMuFF has sent a debug response: [" + data.rstrip() + "]")
			# but do process the tool/endstop states
			elif data[index:].startswith(R_STATES):
				self._parse_states(data.rstrip())
			# and register whether SMuFF is busy
			elif data[index:].startswith(R_BUSY):
				err = "SMuFF has sent a busy response: [" + data.rstrip() + "]"
				self._log.debug(err)
				self.gcode.respond_info(err)
				self._set_busy(True)
			return

		if data.startswith(R_ERROR):
			err = "SMuFF has sent an error response: [" + data.rstrip() + "]"
			self._log.info(err)
			self.gcode.respond_info(err)
			index = len(R_ERROR)+1
			# maybe the SMuFF has received garbage
			if data[index:].startswith(R_UNKNOWNCMD):
				self._serial.reset_output_buffer()
				self._serial.reset_input_buffer()
			self._set_error(True)
			if self._lastCmdSent != None:
				self._lastCmdSent = None
				self._lastCmdDone = True
			return

		if data.startswith(ACTION_CMD):
			self._log.debug("SMuFF has sent an action request: [" + data.rstrip() + "]")
			index = len(ACTION_CMD)
			# what action is it? is it a tool change?
			if data[index:].startswith(TOOL):
				tool = self._parse_tool_number(data[10:])
				# only if the printer isn't printing
				if self._is_printing():
					# query the heater
					heater = self._printer.lookup_object("heater")
					try:
						if heater.extruder.can_extrude:
							self._log.debug("Extruder is up to temp.")
							self._printer.change_tool("tool{0}".format(tool))
							self._send_SMuFF("{0} T: OK".format(ACTION_CMD))
						else:
							self._log.error("Can't change to tool {0}, nozzle not up to temperature".format(tool))
							self._send_SMuFF("{0} T: \"Nozzle too cold\"".format(ACTION_CMD))
					except:
						self._log.error("Can't query temperatures. Aborting.")
						self._send_SMuFF("{0} T: \"No nozzle temp. avail.\"".format(ACTION_CMD))
				else:
					self._log.error("Can't change to tool {0}, printer not ready or printing".format(tool))
					self._send_SMuFF("{0} T: \"Printer not ready\"".format(ACTION_CMD))

			if data[index:].startswith(ACTION_WAIT):
				self._waitRequested = True
				self._log.info("waiting for SMuFF to come clear...")

			if data[index:].startswith(ACTION_CONTINUE):
				self._waitRequested = False
				self._abortRequested = False
				self._log.info("continuing after SMuFF cleared...")

			if data[index:].startswith(ACTION_ABORT):
				self._waitRequested = False
				self._abortRequested = True
				self._log.info("SMuFF is aborting action operation...")

			if data[index:].startswith(ACTION_PONG):
				self._log.info("PONG received from SMuFF")
			return

		if data.startswith(R_JSONCAT):
			self._jsonCat = data[2:].rstrip("*/\n").strip(" ").lower()
			return

		if data.startswith(R_JSON):
			self._parse_json(data, self._jsonCat)
			self._jsonCat = None
			self._initState += 1
			return

		if data.startswith(R_FWINFO):
			self._fwInfo = data.rstrip("\n")
			self.gcode.respond_info(T_FW_INFO.format(self._fwInfo))
			self._lastCmdSent = None
			try:
				arr = re.findall(r"FIRMWARE_NAME\:\s(.*)\sFIRMWARE_VERSION\:\s(.*)\sELECTRONICS\:\s(.*)\sDATE\:\s(.*)\sMODE\:\s(.*)\sOPTIONS\:\s(.*)", self._fwInfo)
				if len(arr):
					self._fwVersion = arr[0][1]
					self._fwBoard 	= arr[0][2]
					self._fwMode 	= arr[0][4]
					self._fwOptions = arr[0][5]
			except Exception as err:
				self._log.error("Can't regex firmware info:\n\t{0}".format(err))
			self._initState += 1
			return

		if data.startswith(R_OK):
			if self._isError:
				self._set_response(None)
				self._lastCmdSent = None
				self._lastCmdDone = True
			else:
				if self._dumpRawData:
					self._log.info("[OK->] LastCommand '{0}'   LastResponse {1}".format(self._lastCmdSent, pformat(self._lastResponse)))

				firstResponse = self._lastResponse[0].rstrip("\n") if len(self._lastResponse) else None

				if self._lastCmdSent == ANY:
					self._lastCmdDone = True
				elif firstResponse != None:
					if firstResponse == self._lastCmdSent:
						self._lastCmdDone = True

				if self._dumpRawData and self._lastCmdSent:
					self._log.info("lastCmdDone is {0}".format(self._lastCmdDone))
				self._set_response("".join(self._lastResponse))
			self._lastCmdSent = None
			# set serEvent only after a ok was received
			self._serEvent.set()
			return

		# store all responses before the "ok"
		if data:
			self._lastResponse.append(str(data))
		self._log.debug("Last response received: [{0}]".format(self._lastResponse[len(self._lastResponse)-1]))

	#
	# Helper function to retrieve time in milliseconds
	#
	def _nowMS(self):
		return int(round(time.time() * 1000))

#
# Main entry point; Creates a new instance of this module.
#
def load_config(config):
	logger = SLogger("SMuFF: {0}")

	try:
		instance = SMuFF(config, logger)
		logger.info("Module instance successfully created")
		if instance and instance.autoConnect:
			logger.info("Auto connecting...")
			instance.start_connector()
		return instance
	except Exception as err:
		logger.error("Unable to create module instance.\n\t{0}".format(err))
		return None
