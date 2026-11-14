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


def test_parse_ipv4_from_ip_addr_output():
    out = "2: eth0    inet 192.168.3.63/24 brd 192.168.3.255 scope global dynamic eth0\\       valid_lft 61743sec\n"
    assert ProxmoxClient._parse_ipv4(out) == "192.168.3.63"


def test_parse_ipv4_none_when_no_address():
    assert ProxmoxClient._parse_ipv4("") is None


def test_parse_setup_token():
    out = (
        "setup token: n905bm37f8jffFB9CDkpS48qxst1yWvp\n"
        "open:        http://192.168.3.63:8080/setup?token=n905bm37f8jffFB9CDkpS48qxst1yWvp\n"
    )
    assert ProxmoxClient._parse_setup_token(out) == {
        "token": "n905bm37f8jffFB9CDkpS48qxst1yWvp",
        "url": "http://192.168.3.63:8080/setup?token=n905bm37f8jffFB9CDkpS48qxst1yWvp",
    }


def test_parse_setup_token_missing():
    assert ProxmoxClient._parse_setup_token("not installed\n") == {"token": None, "url": None}


class _StatusClient(ProxmoxClient):
    """ProxmoxClient with pct status/start faked: stopped until started."""

    def __init__(self):
        super().__init__()
        self.started = 0
        self.running = False

    def get_lxc_status(self, node, vmid):
        return {"data": {"status": "running" if self.running else "stopped"}}

    def start_lxc_container(self, node, vmid):
        self.started += 1
        self.running = True


def test_wait_for_container_starts_and_returns_when_running():
    client = _StatusClient()
    assert client.wait_for_container("n", 1, status="running", timeout=5) is True
    assert client.started == 1


def test_wait_for_container_does_not_restart_running_container():
    client = _StatusClient()
    client.running = True
    assert client.wait_for_container("n", 1, status="running", timeout=5) is True
    assert client.started == 0
