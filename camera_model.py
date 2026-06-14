from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Camera:
    ip: str
    port: int | None = None
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    firmware: str | None = None
    serial_number: str | None = None
    hardware_id: str | None = None
    onvif_url: str | None = None
    rtsp_url: str | None = None
    open_ports: list[int] = field(default_factory=list)
    requires_auth: bool = True
    source: str = "unknown"
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    camera_type: str | None = None
    vendor_confidence: int = 0
    type_confidence: int = 0
    detection_text: str | None = None

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        if self.manufacturer and self.model:
            return f"{self.manufacturer} {self.model}"
        if self.model:
            return self.model
        return f"Camera {self.ip}"

    @property
    def status(self) -> str:
        if self.rtsp_url:
            return "RTSP готов"
        if self.onvif_url:
            return "ONVIF найден"
        if self.open_ports:
            return "Возможная камера"
        return "Неизвестно"

    def merge(self, other: "Camera") -> "Camera":
        self.port = self.port or other.port
        self.name = self.name or other.name
        self.manufacturer = self.manufacturer or other.manufacturer
        self.model = self.model or other.model
        self.firmware = self.firmware or other.firmware
        self.serial_number = self.serial_number or other.serial_number
        self.hardware_id = self.hardware_id or other.hardware_id
        self.onvif_url = self.onvif_url or other.onvif_url
        self.rtsp_url = self.rtsp_url or other.rtsp_url
        self.open_ports = sorted(set(self.open_ports + other.open_ports))
        self.camera_type = self.camera_type or other.camera_type
        self.vendor_confidence = max(self.vendor_confidence, other.vendor_confidence)
        self.type_confidence = max(self.type_confidence, other.type_confidence)
        self.detection_text = self.detection_text or other.detection_text
        if self.source != other.source:
            self.source = f"{self.source}+{other.source}"
        self.last_seen = datetime.now().isoformat(timespec="seconds")
        return self
