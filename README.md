# Welcome to the SMuFF for Klipper project

![The SMuFF](https://github.com/technik-gegg/SMuFF-1.1/raw/SMuFF-3.0/images/SMuFF-V6.png)

This is a module (plugin) for Klipper which handles tool changes on the [SMuFF](https://sites.google.com/view/the-smuff).

This version implements the following (pseudo) GCodes, which can be accessed from the Klipper console:

| GCode | Description |
|-------|-------------|
| SMUFF_CONN | Connect to the SMuFF via serial interface |
| SMUFF_DISC | Disconnect from the SMuFF |
| SMUFF_CUT | Cut filament (if Filament-Cutter is configured) |
| SMUFF_WIPE | Wipe nozzle (if Wiper is installed) |
| SMUFF_LID_OPEN | Open then Lid servo |
| SMUFF_LID_CLOSE | Close the Lid servo |
| SMUFF_SET_SERVO | Position a servo |
| SMUFF_TOOL_CHANGE | Change the current tool (mainly called from T*n* GCode macros) |
| SMUFF_INFO | Query the firmware info from SMuFF |
| SMUFF_STATUS | Query the status from SMuFF |
| SMUFF_SEND | Send GCode to the SMuFF |
| SMUFF_PARAM | Send configuration parameters to the SMuFF |
| SMUFF_MATERIALS | Query the materials configured on the SMuFF |
| SMUFF_SWAPS | Query the tool swaps configured on the SMuFF |
| SMUFF_LIDMAPPINGS | Query the lid servo mappings configured on the SMuFF |
| SMUFF_LOAD | Load filament on active tool on the SMuFF |
| SMUFF_UNLOAD | Unload filament from active tool on the SMuFF |
| SMUFF_HOME | Home Selector (and Revolver if available) |
| SMUFF_MOTORS_OFF | Turn stepper motors on the SMuFF off |
| SMUFF_CLEAR_JAM | Resets the *Feeder Jammed* flag on the SMuFF |
| SMUFF_RESET | Restarts the SMuFF |
| SMUFF_VERSION | Query the SMuFF module version |
| SMUFF_RESET_AVG | Reset tool change statistics |

Most macros don't require any parameter, except these macros:
| GCode | Parameter(s) | Type | Description |
|-------|--------------|------|-------------|
|SMUFF_TOOL_CHANGE|**T**|int|Specifies the tool number to switch to (i.e. *T=2*)|
|SMUFF_SET_SERVO|**SERVO, ANGLE**|int, int|Specify the servo index and the position in degrees (i.e. *SERVO=1 ANGLE=55*)|
|SMUFF_PARAM|**PARAM, VALUE**|string, string|Specify the parameter name and its value to set in the SMuFF (i.e. *PARAM="AnimBPM" VALUE="40"*)|
|SMUFF_SEND|**GCODE**|string|Specifies the GCode to send to the SMuFF (i.e. *GCODE="M119"*)|

When you're using the **SMUFF_PARAM** macro to change settings on the SMuFF on the fly, make sure you call a **SMUFF_SEND GCODE="M500"** afterwards in order to make those settings permanent (SMuFF will then save them to the SD-Card).

 During runtime you have acces to the following properties from within scripts or macros:

| Property | Type | Comment |
|----------|-----|----------------|
|printer.smuff.tools | (int) | The number of tools available on the SMuFF |
|printer.smuff.activetool | (int) | The active tool number, -1 if Selector is homed |
|printer.smuff.pendingtool | (int) | The new tool number requested by a tool change, -1 if no tool change is pending |
|printer.smuff.selector | (bool) | True = triggered |
|printer.smuff.revolver | (bool) | True = triggered |
|printer.smuff.feeder | (bool) | True = triggered |
|printer.smuff.feeder2 | (bool) | True = triggered |
|printer.smuff.fwinfo | (string) | Same as in SMUFF_INFO GCode |
|printer.smuff.isbusy | (bool) | True if SMuFF is doing stuff |
|printer.smuff.iserror | (bool) | True if the last command processed did fail |
|printer.smuff.isprocessing | (bool) | True while processing stuff |
|printer.smuff.isconnected | (bool) | True when connected through serial port |
|printer.smuff.isidle | (bool) | True if SMuFF is in idle state |
|printer.smuff.sdstate | (bool) | True if SD-Card on SMuFF is inserted |
|printer.smuff.lidstate | (bool) | True if Lid is closed |
|printer.smuff.hascutter | (bool) | True if Filament-Cutter is configured |
|printer.smuff.haswiper | (bool) | True if Wiper is configured |
|printer.smuff.hassplitter | (bool) | True if Splitter option is configured |
|printer.smuff.isdde | (bool) | True if DDE is configured |
|printer.smuff.device | (string) | Name of the SMuFF |
|printer.smuff.materials | (array) | Two dimensional array of materials. Index 0 is the tool number, index 1 is an array with: Material, Color, Purge-Factor |
|printer.smuff.swaps | (array) | Array of tool swaps |
|printer.smuff.lidmappings | (array) | Array of lid mappings |
|printer.smuff.version | (float) | Current module version number |
|printer.smuff.fwversion | (string) | Current SMuFF firmware version |
|printer.smuff.fwmode | (string) | Current SMuFF mode setting (SMUFF/PMMU2) |
|printer.smuff.fwoptions | (string) | Options installed on the SMuFF |
|printer.smuff.loadstate | (int) | The current tool filament load state: (***-1** = no tool selected, **0** = not loaded, **1** = loaded to Selector, **2** =  loaded to Nozzle, **3** = loaded to DDE*)  |

**Please keep in mind:** The sheer number of commands and properties results from the fact that the SMuFF has its own controller and processes all commands internally. Klipper only sends SMuFF specific GCodes over the serial interface.
You'll need to access those only if you're about to extend the SMuFF-Klipper module functions for some specific reason.

## Setup

Please visit [this webpage](https://sites.google.com/view/the-smuff/how-to/configure/the-klipper-module) to see the steps that are necessary to install it.
It's a pretty simple and straight forward process, which is accomplished by using the installation script.

For the very first install, open a SSH session on your Raspberry Pi and execute the following commands:

```sh
    cd ~
    git clone https://github.com/technik-gegg/SMuFF-Klipper.git
    cd SMuFF-Klipper
    chmod 755 install-smuff.sh
    ./install-smuff.sh
```

In order to get the SMuFF module updated automatically as I release new versions, it's recommended using the *Moonraker Update Manager* by adding the contents of *moonraker_update_manager.txt* from this repository to your **moonraker.conf** file.

>**Please notice:**
>
>*The configuration files won't be copied if they already exist within the klipper_config folder to prevent overwriting your existing settings on an update!
Hence, if changes within the config files need to be applied, you have to apply them manually. Always check the **Recent Changes** section to see whether you need to apply changes for an updated version.*

---

All the basic settings for the module are located in the **smuff.cfg** file, which eventually has to be included in your **printer.cfg** file. The settings shown in the example below reflect the standard configuration. The only modification you may need to make are for *commandTimeout* and *toolchangeTimeout*. Those depend on the environment your SMuFF is running in.

```Python

[smuff]
serial=/dev/serial/ttySMuFF
baudrate=115200
serialTimeout=10
autoConnectSerial=yes
commandTimeout=25
toolchangeTimeout=90
watchdogTimeout=30
hasCutter=yes
hasWiper=no
debug=no
```

Most of the settings in here are self explanatory. The **autoConnectSerial** will automatically establish a connection to the SMuFF after a restart of Klipper, if set to *yes*.
The latter option **debug** is set to *no* by default. Set this to *yes* if you are troubleshooting and need to know a bit more about what the SMuFF is doing/sending. Turn it back off when you're finished, otherwise it may overwhelm your Klipper log file.

## Troubleshooting

If you run into some issues / strange behaviours when connecting the SMuFF to Klipper, you have to look into the Klipper logfile to fully understand what's going on. The easiest way to do so it to open a SSH connection to your Raspberry Pi and launch the following command:

```sh
tail -f ~/klipper_logs/klippy.log | grep -A5 "SMuFF" || "Trace"
```

This way only SMuFF related logs and Tracebacks (Exceptions) are being shown continously. It helped me a lot while developing the module, so it might be helpful for you too.
*For tracebacks you may have to modify the -A parameter and nudge up the number to see the full trace.*

---

## Recent changes

**V1.13** - Added watchdogTimeout setting to smuff.cfg

- added a new timeout value for the serial port watchdog to *smuff.cfg*, since the existing timeout triggered to soon on some machines that need longer to accomplish a tool load/unload/change operation.
**Please add that setting to your existing *smuff.cfg*** with an initial value of **30** (seconds)
If you still run into these kind of issues, increase this timeout value in steps of 10
- removed **autoLoad** flag from  *smuff.cfg*. Setting this value to *False* doesn't make much sense in a tool change operation
**Please remove that setting from your existing *smuff.cfg* otherwise you'll get an error on startup**
- restructured this Github repository for easier handling from Update Manager
- added the **Moonraker Update Manager** configuration for automatic updates on future releases. See *moonraker_update_manager.txt*

**V1.12** - Added smuff_runout.cfg / Potential bugfix

- added **smuff_runout.cfg**. This macro **may** be used to swap tools sequentially if a runout sensor triggers.
**The thought behind is:** If your runout sensor triggers, the script will determine the next (logical) tool (i.e. activetool + 1) and switch to it. This will allow for continous printing on huge models which may reqiure more than one spool of filament to complete.
**Please notice:** This macro hasn't been tested yet and it'll require that you configure your runout sensor accordingly. If you'd like to use this script, simply add an include in your *printer.cfg*.
- added a return value (eventtime) after reactor timers have been disposed, just in case Klipper is trying to evaluate the return value, which seems to be the case with the latest  version

**V1.11** - Revised serial watchdog / fixed typos

- changed behaviour of serial watchdog, so that it relialbly reconnects when a connection to the SMuFF was lost
- fixed some typos in comments

**V1.1** - Some bug fixes and module extensions

- added GCode to query the module version (since this most probably won't be the last version published)
- added a few more info logs (for easier debugging)
- added automatic retrival of material, swaps and lid-mappings from SMuFF at init
- added GCodes *PRINT_SMUFF_MATERIALS* and *PRINT_SMUFF_SWAPS* to smuff.cfg to demonstrate how to retrieve data from the module via **Jinja** scripting
- changed display menu to show only configured tools (the number of active tools is being read out from the SMuFF)
- separated display menus into *smuff_menu.cfg* (Klipper won't start if it's being configured for headless mode and display menus are defined)
- made the serial communication far more stable/reliable. Klipper won't raise any "**SD Busy**" or "**Shutdown**" messages when printing anymore
- added *version*, *fwversion*, *fwmode*, *fwoptions*, *loadstate*, *isdde* and *hassplitter* variables for scripting
- added macro *PARK_TOOLHEAD* in *smuff.cfg*
- added more useful information to SMUFF_STATUS macro
- added debug option in *smuff.cfg* for more output to log file if needed
- renamed all internal methods with an preceeding underscore (_)
- extracted all texts supposed to be printed in console for easier localization
- updated tool change GCode macros in *smuff.cfg*
- added a tool change counter as well as the average tool change duration time for stats. Keep in mind that these will be reset when Klipper needs a restart. If you want to reset them manually, use the SMUFF_RESET_AVG macro

**V1.0** - Initial release
