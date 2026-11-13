from proxmox.client import ProxmoxClient

PCT_CONFIG_OUTPUT = """arch: amd64
cores: 2
features: keyctl=1,nesting=1
hostname: testtenant-tenant
memory: 4096
net0: name=eth0,bridge=vmbr0,hwaddr=BC:24:11:05:E8:B9,ip=dhcp,type=veth
ostype: debian
rootfs: local-lvm:vm-120-disk-1,size=20G
unprivileged: 1
"""


def test_parse_pct_config():
    config = ProxmoxClient._parse_pct_config(PCT_CONFIG_OUTPUT)
    assert config["features"] == "keyctl=1,nesting=1"
    assert config["net0"] == "name=eth0,bridge=vmbr0,hwaddr=BC:24:11:05:E8:B9,ip=dhcp,type=veth"
    assert config["unprivileged"] == "1"
    assert config["hostname"] == "testtenant-tenant"


def test_parse_pct_config_skips_blank_and_comment_lines():
    config = ProxmoxClient._parse_pct_config("\n#comment: x\ncores: 2\n")
    assert config == {"cores": "2"}
