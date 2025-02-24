# Production Setup Guide

## System Requirements

### Redis Configuration
For optimal Redis performance in production, run these commands on the host machine:

```bash
# Set vm.overcommit_memory
sudo sysctl vm.overcommit_memory=1
# Make it permanent
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf

# Increase max connections
sudo sysctl net.core.somaxconn=511
echo "net.core.somaxconn = 511" | sudo tee -a /etc/sysctl.conf

# Apply changes
sudo sysctl -p
```

### Transparent Huge Pages (THP)
Redis suggests disabling THP. Add this to `/etc/rc.local` before the `exit 0` line:

```bash
if test -f /sys/kernel/mm/transparent_hugepage/enabled; then
    echo never > /sys/kernel/mm/transparent_hugepage/enabled
fi
```

## Security Considerations
1. Make sure Redis is not exposed to public internet
2. Use strong passwords in production
3. Configure firewall rules appropriately
4. Regular backups of Redis data

## Monitoring
Consider setting up monitoring for:
- Redis memory usage
- Connection count
- Cache hit/miss ratio
- Response time
