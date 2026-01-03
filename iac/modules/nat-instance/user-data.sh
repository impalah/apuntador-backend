#!/bin/bash
# NAT Instance User Data Script
# Configures Amazon Linux 2023 to act as a NAT gateway

set -e

echo "🚀 Configuring NAT instance..."

# Enable IP forwarding
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# Get primary network interface (usually ens5 on modern instances)
PRIMARY_IF=$(ip route | grep default | awk '{print $5}' | head -1)
echo "Primary interface detected: $PRIMARY_IF"

# Configure iptables for NAT
# POSTROUTING: Masquerade traffic from VPC going to internet
iptables -t nat -A POSTROUTING -s 10.0.0.0/16 -o $PRIMARY_IF -j MASQUERADE

# FORWARD: Allow traffic from private subnets to internet
iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -s 10.0.0.0/16 -j ACCEPT

# Save iptables rules
iptables-save > /etc/iptables.rules

# Restore iptables on boot
cat > /etc/systemd/system/iptables-restore.service <<'EOF'
[Unit]
Description=Restore iptables rules
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iptables-restore /etc/iptables.rules
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable iptables-restore.service

# Install CloudWatch agent (if monitoring enabled)
%{ if enable_monitoring ~}
yum install -y amazon-cloudwatch-agent
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent
%{ endif ~}

# Configure automatic security updates
yum install -y yum-cron
systemctl enable yum-cron
systemctl start yum-cron

echo "✅ NAT instance configured successfully!"
