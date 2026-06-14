import asyncio
from typing import List, Optional
from camera_model import Camera
from network_utils import get_local_networks
from ws_discovery import discover_onvif_cameras
from subnet_scan import scan_subnet, scan_ipc, scan_nvr, scan_other
from camera_detect import detect_camera
from settings import COMMON_CAMERA_PORTS


class CameraService:

    def __init__(self):
        self.cameras: List[Camera] = []

    def get_local_networks(self) -> List[dict]:
        return get_local_networks()

    async def discover_cameras(
        self,
        cidr: str,
        use_onvif: bool = True,
        use_fallback: bool = True,
        ports: Optional[List[int]] = None
    ) -> List[Camera]:
        selected_ports = ports or COMMON_CAMERA_PORTS
        cameras = []

        if use_onvif:
            try:
                onvif_cameras = discover_onvif_cameras()
                cameras.extend(onvif_cameras)
            except Exception as e:
                print(f"ONVIF discovery failed: {e}")

        if use_fallback:
            try:
                port_cameras = await scan_subnet(cidr, selected_ports)
                cameras.extend(port_cameras)
            except Exception as e:
                print(f"Port scan failed: {e}")

        merged_cameras = self._merge_cameras(cameras)

        for camera in merged_cameras:
            try:
                detect_camera(camera)
            except Exception as e:
                print(f"Camera detection failed for {camera.ip}: {e}")

        self.cameras = merged_cameras
        return self.cameras

    async def discover_ipc(self, cidr: str) -> List[Camera]:
        cameras = await scan_ipc(cidr)
        merged = self._merge_cameras(cameras)
        for camera in merged:
            try:
                detect_camera(camera)
            except Exception as e:
                print(f"Camera detection failed for {camera.ip}: {e}")
        self.cameras = merged
        return self.cameras

    async def discover_nvr(self, cidr: str) -> List[Camera]:
        cameras = await scan_nvr(cidr)
        merged = self._merge_cameras(cameras)
        for camera in merged:
            try:
                detect_camera(camera)
            except Exception as e:
                print(f"Camera detection failed for {camera.ip}: {e}")
        self.cameras = merged
        return self.cameras

    async def discover_other(self, cidr: str) -> List[Camera]:
        cameras = await scan_other(cidr)
        merged = self._merge_cameras(cameras)
        for camera in merged:
            try:
                detect_camera(camera)
            except Exception as e:
                print(f"Camera detection failed for {camera.ip}: {e}")
        self.cameras = merged
        return self.cameras

    async def discover_onvif(self) -> List[Camera]:
        try:
            onvif_cameras = discover_onvif_cameras()
            merged = self._merge_cameras(onvif_cameras)
            for camera in merged:
                try:
                    detect_camera(camera)
                except Exception as e:
                    print(f"Camera detection failed for {camera.ip}: {e}")
            self.cameras = merged
            return self.cameras
        except Exception as e:
            print(f"ONVIF discovery failed: {e}")
            return []

    def _merge_cameras(self, cameras: List[Camera]) -> List[Camera]:
        merged = {}
        for camera in cameras:
            if camera.ip in merged:
                merged[camera.ip].merge(camera)
            else:
                merged[camera.ip] = camera
        return sorted(merged.values(), key=lambda item: item.ip)

    def get_cameras(self) -> List[Camera]:
        return self.cameras.copy()

    def clear_cameras(self):
        self.cameras.clear()
