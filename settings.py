IPC_CAMERA_PORTS =[554 ,8554 ,80 ,443 ,8080 ,8000 ]
NVR_CAMERA_PORTS =[37777 ,34567 ,80 ,443 ,8080 ,8000 ,8200 ]
ALL_CAMERA_PORTS =list (set (IPC_CAMERA_PORTS +NVR_CAMERA_PORTS ))
COMMON_CAMERA_PORTS =ALL_CAMERA_PORTS 
COMMON_RTSP_PATHS =["/stream1","/stream2","/live","/h264","/h264Preview_01_main","/h264Preview_01_sub","/cam/realmonitor?channel=1&subtype=0","/cam/realmonitor?channel=1&subtype=1","/Streaming/Channels/101","/Streaming/Channels/102"]
WS_DISCOVERY_TIMEOUT_SECONDS =3.0 
PORT_SCAN_TIMEOUT_SECONDS =0.35 
MAX_CONCURRENT_SCANS =128 
MAX_HOSTS_TO_SCAN =512 