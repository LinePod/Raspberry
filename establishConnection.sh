#!usr/bin/expect -f
spawn "bluetoothctl"
expect "#"
send "discoverable on\r"
expect "Changing discoverable on succeeded"
send "pairable on\r"
expect "Changing pairable on succeeded"
send "agent on\r"
expect "Agent registered"
