import ipaddress
import socket
import psutil


def get_local_networks() -> list[dict]:
    networks = []
    for interface_name, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family != socket.AF_INET:
                continue
            if not addr.address or not addr.netmask:
                continue
            ip = ipaddress.ip_address(addr.address)
            if ip.is_loopback or ip.is_link_local or ip.is_multicast:
                continue
            network = ipaddress.ip_network(f"{addr.address}/{addr.netmask}", strict=False)
            networks.append({"interface": interface_name, "address": addr.address, "cidr": str(network)})
    return networks


def limited_hosts(cidr: str, max_hosts: int) -> list[str]:
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = [str(ip) for ip in network.hosts()]
    if len(hosts) <= max_hosts:
        return hosts
    return hosts[:max_hosts]
