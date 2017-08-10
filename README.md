# LinePod raspberry

Software that runs on the Raspberry Pi inside the LinePod device.
It:
  * Accepts connections from apps via Bluetooth.
  * Accepts print jobs from connected apps. The contained SVG image is then converted and printed using the Silhouette Portrait.
  * Sends tracking data received from the AirBar to connected apps.

## Installation

Copy `setup.sh` from the root directory onto a fresh Raspbian Jessie system, and run it as the root user.
The script will clone all necessary repositories (including this one) and install everything.

For testing, a virtual machine running Debian Jessie can also be used.

As part of the installation, the system will be updated from Debian Jessie to Debian Stretch.
When official Raspbian images based on Debian Stretch become available, they can be used instead and the relevant code in `setup.sh` be deleted.

## Usage

The setup script registers a systemd service named `linepod.server`, which runs all the necessary scripts.
It is started automatically on startup.

To interact with it, use the normal systemd commands, for example:
  * `systemctl status linepod.server` to retrieve the status of the service,
  * `systemctl [start|stop|restart] linepod.server` to start/stop the server, or
  * `journalctl -u linepod.server` to read the log output.

The main python script run by the service should never be killed (e.g. by `kill` or `killall`).
Otherwise it can cause the AirBar to stop working until the system is restarted, because the kernel USB driver has not been reattached.

## Troubleshooting

Common problems:
  * Is the plotter connected and turned on?
  * Is the AirBar connected and active (makes a beeping sound when a finger exits its tracking range)?
  * Is the Raspberry Pi supplied with enough power, and only from one source?
  * Is Bluetooth up and configured to receive connections (in the output of `hciconfig -a` the relevant device should have the statuses `UP`, `PSCAN` and `ISCAN`)?
