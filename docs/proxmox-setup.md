# Proxmox Setup Instructions

Dit bestand beschrijft de stappen om Proxmox op te zetten op 192.168.1.240 voor de Cyantula Tenant Portal.

## Infrastructure

```
Proxmox Host: 192.168.1.240
VLAN: 30
Network: 192.168.30.0/24
Gateway: 192.168.30.1
DNS: 192.168.1.53
```

## Stappenplan

### 1. Proxmox installeren

Download Proxmox ISO van https://www.proxmox.com/en/downloads

**Installatie:**
- Tijdens installatie VLAN 30 configureren
- IP: 192.168.30.100/24
- Gateway: 192.168.30.1
- Hostname: `proxmox01.cyantula.eu`

### 2. Netwerk configureren

Na installatie, bewerk `/etc/network/interfaces`:

```bash
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet manual

# VLAN 30
auto eth0.30
iface eth0.30 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    gateway 192.168.30.1
    vlan-raw-device eth0

# Bridge voor VMs
auto vmbr0
iface vmbr0 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    bridge_ports eth0.30
    bridge_stp off
    bridge_fd 0

# Route voor VLAN 30
post-up ip route add 192.168.30.0/24 dev vmbr0
```

Herstart netwerk:
```bash
systemctl restart networking
```

### 3. Proxmox updaten

```bash
# Repositories configureren
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-install-repo.list
wget -O- https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg

# Updaten
apt update && apt full-upgrade -y
```

### 4. DNS configureren

Bewerk `/etc/resolv.conf`:
```bash
nameserver 192.168.1.53
search cyantula.eu
```

### 5. SSH toegang

Zorg voor SSH toegang (voor remote beheer):
```bash
# SSH key uploaden
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Voeg je public key toe aan ~/.ssh/authorized_keys
```

### 6. Firewall configureren (optioneel)

```bash
# UFW instellen
ufw allow 22/tcp
ufw allow 8006/tcp
ufw enable
```

### 7. Test Proxmox

Open `https://192.168.30.100:8006` in browser

Login met root credentials

## Volgende stappen

Nadat Proxmox werkt:
1. LXC templates downloaden
2. VM voor tenant portal aanmaken
3. LXC containers configureren voor tenant isolatie

## Problemen

**Geen network na VLAN install:**
- Check `ip a` voor VLAN interface
- Check `/etc/network/interfaces` syntax
- Zorg dat `vlan-raw-device eth0` correct staat

**Proxmox niet bereikbaar:**
- Check firewall regels
- Check `systemctl status pvedaemon`
- Check `journalctl -u pvedaemon`

## Referenties

- https://pve.proxmox.com/pve-docs/
- https://pve.proxmox.com/wiki/Network_Configuration
- https://pve.proxmox.com/wiki/LXC
