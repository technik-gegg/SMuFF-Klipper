# Welcome to the SMuFF for Klipper project

![The SMuFF](https://github.com/technik-gegg/SMuFF-1.1/raw/SMuFF-3.0/images/SMuFF-V6.png)

This is a module (plugin) for Klipper which handles tool changes on the [SMuFF](https://sites.google.com/view/the-smuff).

This version implements the following GCodes which can be accessed from
the Klipper console:

| GCode | Description |
|-------|----------------|
| SMUFF_CONN | Connect to the SMuFF via serial interface |
| SMUFF_DISC | Disconnect from the SMuFF |
| SMUFF_CONNECTED | Show current connection status |
| SMUFF_CUT | Cut filament (if Filament-Cutter is configured) |
| SMUFF_WIPE | Wipe nozzle (if Wiper is installed) |
| SMUFF_LID_OPEN | Open lid servo |
| SMUFF_LID_CLOSE | Close lid servo |
| SMUFF_SET_SERVO | Position a servo |
| SMUFF_TOOL_CHANGE | Change the current tool (mainly called from Tn GCodes) |
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
| SMUFF_CLEAR_JAM | Resets the Feeder Jammed flag on the SMuFF |
| SMUFF_RESET | Resets the SMuFF |

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
|printer.smuff.device | (string) | Name of the SMuFF |

The sheer number of commands and properties results from the fact that the SMuFF has its own controller and processes all commands internally. Klipper only sends SMuFF specific GCodes over the serial interface.

## Setup

Please visit [this webpage](https://sites.google.com/view/the-smuff/how-to/configure/the-klipper-module) to see the steps that are necessary to install it.
It's a pretty simple and stright forward process, which is mostly accomplished by copying a couple of files.

The basic settings of the module are located in the **smuff.cfg** file, which eventually has to be included in your **printer.cfg** file. The settings shown in the example below reflect the standard configuration. The only modification you may need to make are for *commandTimeout* and *toolchangeTimeout*. Those depend on the environment your SMuFF is running in.

```Python

[smuff]
serial=/dev/serial/ttySMuFF
baudrate=115200
serialTimeout=10
commandTimeout=25
toolchangeTimeout=90
autoload=yes
autoconnect=yes
hasCutter=yes
hasWiper=no
```

## Troubleshooting

If you run into some issues / strange behaviours when connecting the SMuFF to Klipper, you have to look into the Klipper logfile to fully understand what's going on. The easiest way to do so it to open a SSH connection to your Raspberry Pi and launch the following command:

```sh
tail -f /home/pi/klipper_logs/klippy.log | grep -A20 "SMuFF" || "Trace"
```

This way only SMuFF related logs and Tracebacks (Exceptions) are being shown continously. It helped me a lot while developing the module, so it might be of help for you too.

***

## Recent changes

**V1.0** - Initial release
