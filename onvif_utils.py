from importlib import resources
from onvif import ONVIFCamera
from rtsp_utils import add_credentials_to_rtsp_url


def get_wsdl_dir() -> str:
    return str(resources.files("onvif").joinpath("wsdl"))


def get_rtsp_uri(ip: str, port: int, username: str, password: str) -> str:
    camera = ONVIFCamera(ip, port, username, password, get_wsdl_dir())
    media_service = camera.create_media_service()
    profiles = media_service.GetProfiles()
    if not profiles:
        raise RuntimeError("Камера не вернула ONVIF media profiles")
    profile = profiles[0]
    request = media_service.create_type("GetStreamUri")
    request.StreamSetup = {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}
    request.ProfileToken = profile.token
    response = media_service.GetStreamUri(request)
    uri = response.Uri
    if username:
        uri = add_credentials_to_rtsp_url(uri, username, password)
    return uri


def get_device_information(ip: str, port: int, username: str, password: str) -> dict:
    camera = ONVIFCamera(ip, port, username, password, get_wsdl_dir())
    device_service = camera.create_devicemgmt_service()
    info = device_service.GetDeviceInformation()
    return {
        "manufacturer": getattr(info, "Manufacturer", None),
        "model": getattr(info, "Model", None),
        "firmware": getattr(info, "FirmwareVersion", None),
        "serial_number": getattr(info, "SerialNumber", None),
        "hardware_id": getattr(info, "HardwareId", None),
    }
