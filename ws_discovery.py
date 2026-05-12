import socket
import time
import uuid
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from camera_model import Camera
from settings import WS_DISCOVERY_TIMEOUT_SECONDS


DISCOVERY_ADDRESS = "239.255.255.250"
DISCOVERY_PORT = 3702


def build_probe_message() -> bytes:
    message_id = uuid.uuid4()
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope" xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery" xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{message_id}</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>'''
    return xml.encode("utf-8")


def text_from_first(root: ET.Element, suffix: str) -> str | None:
    for elem in root.iter():
        if elem.tag.endswith(suffix) and elem.text:
            return elem.text.strip()
    return None


def parse_camera_response(data: bytes, fallback_ip: str) -> Camera | None:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    xaddrs_text = text_from_first(root, "XAddrs")
    scopes_text = text_from_first(root, "Scopes")
    if not xaddrs_text:
        return None
    xaddrs = xaddrs_text.split()
    onvif_url = xaddrs[0]
    parsed = urlparse(onvif_url)
    ip = parsed.hostname or fallback_ip
    port = parsed.port or 80
    name = None
    model = None
    manufacturer = None
    if scopes_text:
        for scope in scopes_text.split():
            lowered = scope.lower()
            value = scope.rsplit("/", 1)[-1].replace("_", " ")
            if "name" in lowered and not name:
                name = value
            elif "model" in lowered and not model:
                model = value
            elif "hardware" in lowered and not model:
                model = value
            elif "manufacturer" in lowered and not manufacturer:
                manufacturer = value
    return Camera(ip=ip, port=port, name=name, manufacturer=manufacturer, model=model, onvif_url=onvif_url, open_ports=[port], source="onvif")


def discover_onvif_cameras(timeout: float = WS_DISCOVERY_TIMEOUT_SECONDS) -> list[Camera]:
    found = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(0.5)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    try:
        sock.sendto(build_probe_message(), (DISCOVERY_ADDRESS, DISCOVERY_PORT))
        end_at = time.time() + timeout
        while time.time() < end_at:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            camera = parse_camera_response(data, addr[0])
            if camera:
                if camera.ip in found:
                    found[camera.ip].merge(camera)
                else:
                    found[camera.ip] = camera
    finally:
        sock.close()
    return list(found.values())
