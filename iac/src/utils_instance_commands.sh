#!/bin/bash
yum install -y amazon-efs-utils
mkdir -p /mnt/efs
mount -t efs ${file_system_id}:/ /mnt/efs
echo "/mnt/fs before chmod"
ls -la /mnt/efs
echo "${file_system_id}:/ /mnt/efs efs defaults,_netdev 0 0" >> /etc/fstab
chmod 777 /mnt/efs
echo "/mnt/fs after chmod"
ls -la /mnt/efs
