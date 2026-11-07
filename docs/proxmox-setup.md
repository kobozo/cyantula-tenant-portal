# Proxmox Setup Instructions

Dit bestand beschrijft de Proxmox configuratie voor de Cyantula Tenant Portal.

## Infrastructure

```
Proxmox Host: 192.168.1.240
VLAN: 30
Network: 192.168.30.0/24
Gateway: 192.168.30.1
DNS: 192.168.1.53
```

## Configuratie

### 1. Netwerk (VLAN 30)

Bewerk `/etc/network/interfaces`:

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

# Bridge voor VMs/LXC
auto vmbr0
iface vmbr0 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    bridge_ports eth0.30
    bridge_stp off
    bridge_fd 0
```

### 2. DNS

```bash
nameserver 192.168.1.53
search cyantula.eu
```

### 3. Proxmox updaten

```bash
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-install-repo.list
wget -O- https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
apt update && apt full-upgrade -y
```

## VLAN 30 setup (op bestaande Proxmox installatie)

Als Proxmox al draait op 192.168.1.240, voeg VLAN 30 toe:

```bash
# Bestaande eth0 config bewaren (als die er is)
# Voeg VLAN interface toe
auto eth0.30
iface eth0.30 inet static
    address 192.168.30.100
    netmask 255.255.255.0
    gateway 192.168.30.1
    vlan-raw-device eth0
```

## Gebruik

Deze Proxmox host wordt gebruikt door CI/CD om LXC containers te provisoneren.

**Geen handmatige templates aanmaken!** Templates worden gegenereerd via CI.

## Voorbereiding voor CI

Zorg dat:
1. Proxmox API beschikbaar is op `https://192.168.30.100:8006`
2. Root account met wachtwoord beschikbaar is
3. VLAN 30 network werkt
4. SSH toegang mogelijk is (voor debugging)

## Volgende stappen

Nadat Proxmox werkt:
1. CI/CD pipeline configuren voor LXC provisioning
2. Templates genereren via CI
3. Automatische tenant onboarding
