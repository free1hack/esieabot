#!/bin/bash
echo none | sudo tee /sys/class/leds/led0/trigger
rm -f /esieabot/once/zzz-shutdown.sh; halt
