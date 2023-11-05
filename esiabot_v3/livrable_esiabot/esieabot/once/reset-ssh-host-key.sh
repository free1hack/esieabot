#!/bin/bash
# This script renew SSH host key
set -e
rm /etc/ssh/ssh_host_*
ssh-keygen -A
