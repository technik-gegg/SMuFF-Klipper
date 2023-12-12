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
# 	SMUFF_INSTANCE		- Sets the active instance on an IDEX machine
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
#	watchdogTimeout=30
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

import logging

from . import smuff_core			# main functions are located in this module
IS_KLIPPER		= True 				# flag has to be set to True for Klipper

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
		self._log 			= logger
		self.SCA 			= smuff_core.SmuffCore(logger, IS_KLIPPER, self.smuffStatusCallbackA, self.smuffResponseCallbackA, config)
		self.SCB 			= smuff_core.SmuffCore(logger, IS_KLIPPER, self.smuffStatusCallbackB, self.smuffResponseCallbackB, config)
		self._activeInstance = "A"
		self._instance 		= self.SCA
		self._hasIDEX 		= False
		self._printer 		= config.get_printer()
		self._reactor 		= self._printer.get_reactor()
		self.gcode 			= self._printer.lookup_object("gcode")
		self._lastActiveA 	= False
		self._lastActiveB 	= False

		try:
			self.pause_resume = self._printer.load_object(config, "pause_resume")
		except config.error:
			raise self._printer.config_error(smuff_core.T_CFG_GCODE_ERR.format("PAUSE_RESUME"))


		# get configuration
		self._ignoreDebug = config.get("ignoreDebug", default=smuff_core.T_NO).upper() == smuff_core.T_YES
		self._hasIDEX = config.get("hasIDEX", default=smuff_core.T_NO).upper() == smuff_core.T_YES
		serialPort = config.get("serial")
		if not serialPort:
			raise config.error(smuff_core.T_CFG_ERR)
		self.SCA.serialPort 	= serialPort
		self.SCA.baudrate		= config.getint("baudrate", default=115200)
		self.SCA.timeout		= config.getfloat("serialTimeout", default=5.0)
		self.SCA.cmdTimeout		= config.getfloat("commandTimeout", default=20.0)
		self.SCA.tcTimeout		= config.getfloat("toolchangeTimeout", default=90.0)
		self.SCA.autoConnect	= config.get("autoConnectSerial", default=smuff_core.T_YES).upper() == smuff_core.T_YES
		self.SCA.hasCutter		= config.get("hasCutter", default=smuff_core.T_YES).upper() == smuff_core.T_YES 		# will be eventually overwritten by the SMuFF config
		self.SCA.hasWiper 		= config.get("hasWiper", default=smuff_core.T_NO).upper() == smuff_core.T_YES
		self.SCA.dumpRawData 	= config.get("debug", default=smuff_core.T_NO).upper() == smuff_core.T_YES
		self.SCA.wdTimeout 		= config.getfloat("watchdogTimeout", default=60)
		self.SCA.ignoreDebug 	= self._ignoreDebug

		# 2nd serial port gets only handled if hasIDEX is set
		if self._hasIDEX:
			serialPortB = config.get("serialB")
			if serialPortB:
				self.SCB.serialPort 	= serialPortB
				self.SCB.baudrate		= config.getint("baudrateB", default=115200)
				self.SCB.timeout		= config.getfloat("serialTimeoutB", default=5.0)
				self.SCB.cmdTimeout		= config.getfloat("commandTimeoutB", default=20.0)
				self.SCB.tcTimeout		= config.getfloat("toolchangeTimeoutB", default=90.0)
				self.SCB.autoConnect	= config.get("autoConnectSerialB", default=smuff_core.T_YES).upper() == smuff_core.T_YES
				self.SCB.hasCutter		= config.get("hasCutterB", default=smuff_core.T_YES).upper() == smuff_core.T_YES 		# will be eventually overwritten by the SMuFF config
				self.SCB.hasWiper 		= config.get("hasWiperB", default=smuff_core.T_NO).upper() == smuff_core.T_YES
				self.SCB.dumpRawData 	= self.SCA.dumpRawData
				self.SCB.wdTimeout 		= config.getfloat("watchdogTimeoutB", default=60)
				self.SCB.ignoreDebug 	= self._ignoreDebug

		# register Klipper event handlers
		self._printer.register_event_handler("klippy:disconnect", self.event_disconnect)
		self._printer.register_event_handler("klippy:connect", self.event_connect)
		self._printer.register_event_handler("klippy:ready", self.event_ready)

		# register GCodes for SMuFF
		self.gcode.register_command("SMUFF_CONN",           self.cmd_connect,     	smuff_core.T_HELP_CONN)
		self.gcode.register_command("SMUFF_DISC",           self.cmd_disconnect,  	smuff_core.T_HELP_DISC)
		self.gcode.register_command("SMUFF_CONNECTED",      self.cmd_connected,  	smuff_core.T_HELP_CONNECTED)
		self.gcode.register_command("SMUFF_CUT",            self.cmd_cut,         	smuff_core.T_HELP_CUT)
		self.gcode.register_command("SMUFF_WIPE",           self.cmd_wipe,        	smuff_core.T_HELP_WIPE)
		self.gcode.register_command("SMUFF_LID_OPEN",       self.cmd_lid_open,    	smuff_core.T_HELP_LID_OPEN)
		self.gcode.register_command("SMUFF_LID_CLOSE",      self.cmd_lid_close,   	smuff_core.T_HELP_LID_CLOSE)
		self.gcode.register_command("SMUFF_SET_SERVO",      self.cmd_servo_pos,   	smuff_core.T_HELP_SET_SERVO)
		self.gcode.register_command("SMUFF_TOOL_CHANGE",    self.cmd_tool_change, 	smuff_core.T_HELP_TOOL_CHANGE)
		self.gcode.register_command("SMUFF_INFO",           self.cmd_fw_info,     	smuff_core.T_HELP_INFO)
		self.gcode.register_command("SMUFF_STATUS",         self.cmd_get_states,  	smuff_core.T_HELP_STATUS)
		self.gcode.register_command("SMUFF_SEND",           self.cmd_gcode,       	smuff_core.T_HELP_SEND)
		self.gcode.register_command("SMUFF_PARAM",          self.cmd_param,       	smuff_core.T_HELP_PARAM)
		self.gcode.register_command("SMUFF_MATERIALS",      self.cmd_materials,     smuff_core.T_HELP_MATERIALS)
		self.gcode.register_command("SMUFF_SWAPS",      	self.cmd_swaps,     	smuff_core.T_HELP_SWAPS)
		self.gcode.register_command("SMUFF_LIDMAPPINGS",   	self.cmd_lidmappings,   smuff_core.T_HELP_LIDMAPPINGS)
		self.gcode.register_command("SMUFF_LOAD",   		self.cmd_load,   		smuff_core.T_HELP_LOAD)
		self.gcode.register_command("SMUFF_UNLOAD",   		self.cmd_unload,   		smuff_core.T_HELP_UNLOAD)
		self.gcode.register_command("SMUFF_HOME",   		self.cmd_home,   		smuff_core.T_HELP_HOME)
		self.gcode.register_command("SMUFF_MOTORS_OFF", 	self.cmd_motors_off, 	smuff_core.T_HELP_MOTORS_OFF)
		self.gcode.register_command("SMUFF_CLEAR_JAM",		self.cmd_clear_jam, 	smuff_core.T_HELP_CLEAR_JAM)
		self.gcode.register_command("SMUFF_RESET",			self.cmd_reset, 		smuff_core.T_HELP_RESET)
		self.gcode.register_command("SMUFF_VERSION",		self.cmd_version, 		smuff_core.T_HELP_VERSION)
		self.gcode.register_command("SMUFF_RESET_AVG",		self.cmd_reset_avg, 	smuff_core.T_HELP_RESET_AVG)
		self.gcode.register_command("SMUFF_DUMP_RAW",		self.cmd_dump_raw, 		smuff_core.T_HELP_DUMP_RAW)
		self.gcode.register_command("SMUFF_DEBUG",			self.cmd_dump_raw, 		smuff_core.T_HELP_DUMP_RAW)
		self.gcode.register_command("SMUFF_INSTANCE",		self.cmd_instance, 		smuff_core.T_HELP_INSTANCE)
		self.gcode.register_command("SMUFF_GETINSTANCE",	self.cmd_getinstance, 	smuff_core.T_HELP_GETINSTANCE)
		self.gcode.register_command("SMUFF_TEST",			self.cmd_test, 			"")

	def autoConnect(self):
		if self.SCA.autoConnect:
			self._log.info("Auto connecting SMuFF A...")
			self.SCA.connect_SMuFF()
		if self._hasIDEX and self.SCB.autoConnect:
			self._log.info("Auto connecting SMuFF B...")
			self.SCB.connect_SMuFF()

	def smuffStatusCallbackA(self, active):
		if self._lastActiveA != active:
			self._log.info("[ A ]  active state switched from {0} to {1}".format(self._lastActiveA, active))
			self._lastActiveA = active
			if active == False:
				self._setResponse("Serial reader has shut down", False, self.SCA)

	def smuffStatusCallbackB(self, active):
		if self._lastActiveB != active:
			self._log.info("[ B ]  active state switched from {0} to {1}".format(self._lastActiveB, active))
			self._lastActiveB = active
			if active == False:
				self._setResponse("Serial reader has shut down", False, self.SCB)

	def smuffResponseCallbackA(self, message):
		self._setResponse(message, False, self.SCA)

	def smuffResponseCallbackB(self, message):
		self._setResponse(message, False, self.SCB)

	#
	# Send a response (text) to Klipper GCode panel
	#
	def _setResponse(self, response, addPrefix = False, instance = None):
		fromInst = ""
		if self._hasIDEX and not instance == None:
			fromInst = " [ A ]  " if instance == self.SCA else " [ B ]  "
		if response != "":
			self.gcode.respond_info(fromInst + response)

	def _reset(self):
		self._log.info("Resetting module")

    #
    # Klippy disconnect handler
    #
	def event_disconnect(self):
		# make sure to clean up ressources (i.e. serial reader thread) otherwise
		# it'll interfere with the new instance after firmware restart
		self._log.info("Klippy has disconnected, closing serial communication to SMuFF")
		self.SCA.close_serial()
		self.SCB.close_serial()

    #
    # Klippy connect handler
    #
	def event_connect(self):
		# no further action in here
		self._log.info("Klippy has connected")

    #
    # Klippy ready handler
    #
	def event_ready(self):
		# check presence of PRE/POST_TOOLCHANGE macros
		self._log.info("Klippy is ready")
		if not smuff_core.PRE_TC in self.gcode.ready_gcode_handlers:
			raise self._printer.config_error(smuff_core.T_CFG_GCODE_ERR.format("gcode_macro '{0}'".format(smuff_core.PRE_TC)))
		else:
			self._log.info("gcode_macro '{0}' check OK".format(smuff_core.PRE_TC))
		if not smuff_core.POST_TC in self.gcode.ready_gcode_handlers:
			raise self._printer.config_error(smuff_core.T_CFG_GCODE_ERR.format("gcode_macro '{0}'".format(smuff_core.POST_TC)))
		else:
			self._log.info("gcode_macro '{0}' check OK".format(smuff_core.POST_TC))


	def get_instance(self, gcmd=None):
		if gcmd:
			device = gcmd.get(smuff_core.P_DEVICE, default="A").upper()
			if device == "A" or device == "B":
				self._activeInstance = device
			else:
				self.gcode.respond_info(smuff_core.T_INVALID_DEVICE)
		else:
			self._activeInstance = "A"  # make the first device the default
		self._instance = self.SCA if self._activeInstance == "A" else self.SCB

	def set_instance(self, inst):
		self._activeInstance = inst

	def chk_connection(self, gcmd=None):
		self.get_instance(gcmd)
		if not self._instance.isConnected:
			self._setResponse(smuff_core.T_NOT_CONN, False, self._instance)
			return False
		return True

    #
    # SMUFF_CONN
    #
	def cmd_connect(self, gcmd=None, autoConnect=None):
		self.get_instance(gcmd)
		if self._instance.isConnected:
			self._setResponse(smuff_core.T_ALDY_CONN, False, self._instance)
			return True

		status = self._instance.connect_SMuFF(gcmd)
		if status:
			self._setResponse(smuff_core.T_CONN, False, self._instance)
			return True
		else:
			self._setResponse(smuff_core.T_NOT_CONN, False, self._instance)
		return False

    #
    # SMUFF_DISC
    #
	def cmd_disconnect(self, gcmd=None):
		self.get_instance(gcmd)
		self._instance.close_serial()

    #
    # SMUFF_CONNECTED
    #
	def cmd_connected(self, gcmd):
		self.get_instance(gcmd)
		if self._instance.isConnected:
			self._setResponse(smuff_core.T_IS_CONN.format(self._instance.serialPort), False, self._instance)
		else:
			self._setResponse(smuff_core.T_ISNT_CONN, False, self._instance)

    #
    # SMUFF_CUT
    #
	def cmd_cut(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._setResponse(smuff_core.T_CUTTING, False, self._instance)
		self._instance.send_SMuFF(smuff_core.CUT)

    #
    # SMUFF_WIPE
    #
	def cmd_wipe(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._setResponse(smuff_core.T_WIPING, False, self._instance)
		self._instance.send_SMuFF(smuff_core.WIPE)

    #
    # SMUFF_LID_OPEN
    #
	def cmd_lid_open(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._setResponse(smuff_core.T_OPENING_LID, False, self._instance)
		self._instance.send_SMuFF(smuff_core.LIDOPEN)

    #
    # SMUFF_LID_CLOSE
    #
	def cmd_lid_close(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._setResponse(smuff_core.T_CLOSING_LID, False, self._instance)
		self._instance.send_SMuFF(smuff_core.LIDCLOSE)

    #
    # SMUFF_SET_SERVO
    #
	def cmd_servo_pos(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		if gcmd:
			servo = gcmd.get_int(smuff_core.P_SERVO, default=1) 	# Lid servo by default
			pos = gcmd.get_int(smuff_core.P_ANGLE, default=90)
			if pos < 0 or pos > 180:
				gcmd.respond_info(smuff_core.T_ERR_SERVOPOS)
				return
			self._setResponse(smuff_core.T_POSITIONING.format(servo, pos), False, self._instance)
			self._instance.send_SMuFF(smuff_core.SETSERVO.format(servo, pos))

    #
    # SMUFF_TOOL_CHANGE
    #
	def cmd_tool_change(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.klipper_change_tool(gcmd)

    #
    # SMUFF_INFO
    #
	def cmd_fw_info(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._setResponse(smuff_core.T_FW_INFO.format(self._instance.get_fw_info()), False, self._instance)

    #
    # SMUFF_STATUS
    #
	def cmd_get_states(self, gcmd=None):
		self.get_instance(gcmd)
		connStat = self._instance.get_states(gcmd)
		self._setResponse(connStat, False, self._instance)

    #
    # SMUFF_SEND
    #
	def cmd_gcode(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		if gcmd == None:
			return
		gcode = gcmd.get(smuff_core.P_GCODE)
		if not gcode:
			gcmd.respond_info(smuff_core.T_NO_PARAM.format(smuff_core.P_GCODE))
			return
		if gcode.upper() == smuff_core.RESET:
			self._instance.send_SMuFF(gcode)
		else:
			response = self._instance.send_SMuFF_and_wait(gcode)
			if response:
				gcmd.respond_info(smuff_core.T_SMUFF_RESPONSE.format(response))

    #
    # SMUFF_PARAM
    #
	def cmd_param(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		if gcmd == None:
			return
		param = gcmd.get(smuff_core.P_PARAM)
		paramVal = gcmd.get(smuff_core.P_PARAMVAL)
		if not param:
			gcmd.respond_info(smuff_core.T_NO_PARAM.format(smuff_core.P_PARAM))
			return
		if not paramVal:
			gcmd.respond_info(smuff_core.T_NO_VALUE.format(smuff_core.P_PARAMVAL))
			return
		response = self._instance.send_SMuFF_and_wait(smuff_core.SETPARAM.format(param, paramVal))
		if self._instance.isError:
			gcmd.respond_info(smuff_core.T_SMUFF_ERR.format(response))

    #
    # SMUFF_MATERIALS
    #
	def cmd_materials(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.GETCONFIG.format(smuff_core.CFG_MATERIALS))

    #
    # SMUFF_SWAPS
    #
	def cmd_swaps(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.GETCONFIG.format(smuff_core.CFG_SWAPS))

    #
    # SMUFF_LIDMAPPINGS
    #
	def cmd_lidmappings(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.GETCONFIG.format(smuff_core.CFG_SERVOMAPS))

    #
    # SMUFF_LOAD
    #
	def cmd_load(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		if not self._instance._okTimer is None:
			self._setResponse(smuff_core.T_NOT_READY, False, self._instance)
			return
		activeTool = self._instance.get_active_tool()
		if activeTool != -1:
			self._instance.send_SMuFF(smuff_core.LOADFIL)
			self._instance._okTimer = self._reactor.register_timer(self._instance.wait_for_ok, self._reactor.NOW + 5.0)

    #
    # SMUFF_UNLOAD
    #
	def cmd_unload(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		if not self._instance._okTimer is None:
			self._setResponse(smuff_core.T_NOT_READY, False, self._instance)
			return
		activeTool = self._instance.get_active_tool()
		if activeTool != -1:
			self._instance.send_SMuFF(smuff_core.UNLOADFIL)
			self._instance._okTimer = self._reactor.register_timer(self._instance.wait_for_ok, self._reactor.NOW + 5.0)

    #
    # SMUFF_HOME
    #
	def cmd_home(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.HOME)

    #
    # SMUFF_MOTORS_OFF
    #
	def cmd_motors_off(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.MOTORSOFF)

    #
    # SMUFF_CLEAR_JAM
    #
	def cmd_clear_jam(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.UNJAM)

    #
    # SMUFF_RESET
    #
	def cmd_reset(self, gcmd=None):
		if not self.chk_connection(gcmd):
			return
		self._instance.send_SMuFF(smuff_core.RESET)

    #
    # SMUFF_VERSION
    #
	def cmd_version(self, gcmd=None):
		self.get_instance(gcmd)
		self._setResponse(smuff_core.VERSION_STRING.format(smuff_core.VERSION_NUMBER, smuff_core.VERSION_DATE), False, self._instance)

    #
    # SMUFF_RESET_AVG
    #
	def cmd_reset_avg(self, gcmd=None):
		self.get_instance(gcmd)
		self._instance.reset_avg()
		self._setResponse(smuff_core.T_OK, False, self._instance)

    #
    # SMUFF_DUMP_RAW
    #
	def cmd_dump_raw(self, gcmd=None):
		self.SCA.dumpRawData = not self.SCA.dumpRawData
		self.SCB.dumpRawData = not self.SCB.dumpRawData
		self.gcode.respond_info(smuff_core.T_DUMP_RAW.format(smuff_core.T_ON if self.SCA.dumpRawData else smuff_core.T_OFF))

    #
    # SMUFF_INSTANCE
    #
	def cmd_instance(self, gcmd=None):
		if self._hasIDEX == False:
			self.gcode.respond_info(smuff_core.T_NO_IDEX)
			return
		if gcmd == None:
			return
		param = gcmd.get(smuff_core.P_PARAMVAL).upper()
		if param == "A" or param == "B":
			self.set_instance(param)
		else:
			self.gcode.respond_info(smuff_core.T_INVALID_DEVICE)
			return
		self.gcode.respond_info(smuff_core.T_OK)

    #
    # SMUFF_GETINSTANCE
    #
	def cmd_getinstance(self, gcmd=None):
		self.gcode.respond_info(smuff_core.T_ACTIVE_INSTANCE.format(self._activeInstance))

    #
    # SMUFF_TEST
    #
	def cmd_test(self, gcmd=None):
		self.gcode.respond_info(smuff_core.T_OK)

	#
	# Set status values to be used within Klipper (scripts, GCode)
	#
	def get_status(self, eventtime=None):
		#self._log.info("get_status being called. M:{0} S:{1} ")
		self.get_instance(None)
		return self._instance.get_status()



#
# Main entry point; Creates a new instance of this module.
#
def load_config(config):
	logger = SLogger("SMuFF: {0}")

	try:
		instance = SMuFF(config, logger)
		logger.info("Module instance successfully created")
		if instance:
			instance.autoConnect()
		return instance
	except Exception as err:
		logger.error("Unable to create module instance.\n\t{0}".format(err))
		return None
