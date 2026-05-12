import asyncio
from camera_model import Camera
from network_utils import limited_hosts
from settings import IPC_CAMERA_PORTS, NVR_CAMERA_PORTS, ALL_CAMERA_PORTS, MAX_CONCURRENT_SCANS, MAX_HOSTS_TO_SCAN, PORT_SCAN_TIMEOUT_SECONDS


async def is_port_open(ip: str, port: int, timeout: float = PORT_SCAN_TIMEOUT_SECONDS) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def scan_host(ip: str, ports: list[int], semaphore: asyncio.Semaphore) -> Camera | None:
    async with semaphore:
        open_ports = []
        for port in ports:
            if await is_port_open(ip, port):
                open_ports.append(port)
        if not open_ports:
            return None
        rtsp_like = 554 in open_ports or 8554 in open_ports
        web_like = 80 in open_ports or 443 in open_ports or 8080 in open_ports or 8000 in open_ports or 8899 in open_ports or 37777 in open_ports or 34567 in open_ports
        if not rtsp_like and not web_like:
            return None
        main_port = 554 if 554 in open_ports else open_ports[0]
        return Camera(ip=ip, port=main_port, name=f"Possible camera {ip}", open_ports=open_ports, source="port_scan")


async def scan_subnet(cidr: str, ports: list[int] | None = None, max_hosts: int = MAX_HOSTS_TO_SCAN) -> list[Camera]:
    selected_ports = ports or ALL_CAMERA_PORTS
    hosts = limited_hosts(cidr, max_hosts)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)
    tasks = [scan_host(ip, selected_ports, semaphore) for ip in hosts]
    results = await asyncio.gather(*tasks)
    return [camera for camera in results if camera is not None]


async def scan_ipc(cidr: str, max_hosts: int = MAX_HOSTS_TO_SCAN) -> list[Camera]:
    hosts = limited_hosts(cidr, max_hosts)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)
    tasks = [scan_host(ip, IPC_CAMERA_PORTS, semaphore) for ip in hosts]
    results = await asyncio.gather(*tasks)
    cameras = [camera for camera in results if camera is not None]
    for camera in cameras:
        camera.source = "ipc_scan"
    return cameras


async def scan_nvr(cidr: str, max_hosts: int = MAX_HOSTS_TO_SCAN) -> list[Camera]:
    hosts = limited_hosts(cidr, max_hosts)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)
    tasks = [scan_host(ip, NVR_CAMERA_PORTS, semaphore) for ip in hosts]
    results = await asyncio.gather(*tasks)
    cameras = [camera for camera in results if camera is not None]
    for camera in cameras:
        camera.source = "nvr_scan"
    return cameras


async def scan_other(cidr: str, max_hosts: int = MAX_HOSTS_TO_SCAN) -> list[Camera]:
    hosts = limited_hosts(cidr, max_hosts)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)
    all_ports = sorted(set(IPC_CAMERA_PORTS + NVR_CAMERA_PORTS + [8899, 5000, 9000]))
    tasks = [scan_host(ip, all_ports, semaphore) for ip in hosts]
    results = await asyncio.gather(*tasks)
    cameras = [camera for camera in results if camera is not None]
    for camera in cameras:
        camera.source = "other_scan"
    return cameras