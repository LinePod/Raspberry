# linespace_raspberry

## What this script does

- Connecting to Android phones over bluetooth
- Connecting to Silhouette Portrait over USB
- Connecting to AirBar over USB
- Receiving SVGs to be printed from bluetooth devices
- Converting SVGs to GPGL commands
- Sending GPGL commands to Silhouette Portrait
- Receiving Tracking data from AirBar
- Sending Tracking data to connected bluetooth device

## Installation

- run ./setup.sh with admin priviledges to setup program.

## Usage

- Script will run automatically on startup
- Do not kill with ```sudo killall python``` as the kernel driver for the usb devices need to be reattached. Otherwise, the airbar will not be usable anymore and the system needs to be restarted

## Troubleshooting

- The program logs to journalctl. If any problems occur, check the logs with journalctl.
- Is the plotter connected and turned on?
- Is the AirBar connected?
- Is the RaspberryPI supplied with enough power?
