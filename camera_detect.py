import socket 
import ssl 
import urllib .request 
from html .parser import HTMLParser 
from urllib .error import HTTPError ,URLError 


VENDOR_KEYWORDS ={
"hikvision":"Hikvision",
"hivision":"Hikvision",
"hiwatch":"Hikvision",
"dahua":"Dahua",
"axis":"Axis",
"reolink":"Reolink",
"foscam":"Foscam",
"amcrest":"Amcrest",
"uniview":"Uniview",
"ubiquiti":"Ubiquiti",
"unifi":"Ubiquiti",
"vivotek":"Vivotek",
"bosch":"Bosch",
"sony":"Sony",
"panasonic":"Panasonic",
"tp-link":"TP-Link",
"tplink":"TP-Link",
"tapo":"TP-Link Tapo",
"ezviz":"EZVIZ",
"hanwha":"Hanwha",
"samsung":"Samsung",
"pelco":"Pelco",
"mobotix":"Mobotix",
"geovision":"GeoVision",
"grandstream":"Grandstream",
"lorex":"Lorex",
"swann":"Swann",
"trendnet":"TRENDnet",
"xmeye":"XMEye",
"xmjp":"Xiongmai",
"netwave":"Netwave",
"avtech":"AVTech",
"zmodo":"Zmodo",
"wanscam":"Wanscam",
"annke":"Annke"
}


class TitleParser (HTMLParser ):
    def __init__ (self ):
        super ().__init__ ()
        self .in_title =False 
        self .title =""

    def handle_starttag (self ,tag ,attrs ):
        if tag .lower ()=="title":
            self .in_title =True 

    def handle_endtag (self ,tag ):
        if tag .lower ()=="title":
            self .in_title =False 

    def handle_data (self ,data ):
        if self .in_title :
            self .title +=data .strip ()


def fetch_http_fingerprint (ip :str ,port :int ,timeout :float =1.2 )->str :
    scheme ="https"if port ==443 else "http"
    url =f"{scheme }://{ip }:{port }/"
    context =ssl ._create_unverified_context ()if scheme =="https"else None 
    try :
        request =urllib .request .Request (url ,headers ={"User-Agent":"IPCameraViewer/1.0"},method ="GET")
        with urllib .request .urlopen (request ,timeout =timeout ,context =context )as response :
            headers =dict (response .headers .items ())
            body =response .read (8192 ).decode ("utf-8",errors ="ignore")
        parser =TitleParser ()
        parser .feed (body )
        parts =[
        headers .get ("Server",""),
        headers .get ("WWW-Authenticate",""),
        headers .get ("X-Frame-Options",""),
        headers .get ("X-Content-Type-Options",""),
        headers .get ("Set-Cookie",""),
        parser .title ,
        body [:2048 ]
        ]
        return " ".join (part for part in parts if part )
    except HTTPError as error :
        headers =dict (error .headers .items ())
        return " ".join ([
        headers .get ("Server",""),
        headers .get ("WWW-Authenticate",""),
        headers .get ("Set-Cookie",""),
        str (error .code )
        ])
    except (URLError ,TimeoutError ,socket .timeout ,OSError ,ValueError ):
        return ""


def guess_vendor (text :str )->tuple [str |None ,int ]:
    lowered =text .lower ()
    for keyword ,vendor in VENDOR_KEYWORDS .items ():
        if keyword in lowered :
            return vendor ,90 
    return None ,0 


def guess_camera_type (camera )->tuple [str ,int ]:
    ports =camera .open_ports or []
    if camera .onvif_url :
        return "ONVIF IP Camera",95 
    if 554 in ports or 8554 in ports :
        return "IP Camera (RTSP)",85 
    if 37777 in ports or 34567 in ports :
        return "NVR/XVR/HVR/DVR",90 
    if 80 in ports or 443 in ports or 8080 in ports or 8000 in ports :
        return "Possible IP Camera",60 
    if 8899 in ports or 5000 in ports or 9000 in ports :
        return "Other device",40 
    return "Unknown network device",20 


def detect_camera (camera ):
    parts =[
    camera .ip or "",
    camera .name or "",
    camera .manufacturer or "",
    camera .model or "",
    camera .onvif_url or ""
    ]
    for port in camera .open_ports or []:
        if port in [80 ,443 ,8080 ,8000 ,8899 ]:
            parts .append (fetch_http_fingerprint (camera .ip ,port ))
    text =" ".join (parts )
    vendor ,vendor_confidence =guess_vendor (text )
    camera_type ,type_confidence =guess_camera_type (camera )
    if vendor :
        camera .manufacturer =camera .manufacturer or vendor 
    camera .camera_type =camera_type 
    camera .vendor_confidence =vendor_confidence 
    camera .type_confidence =type_confidence 
    camera .detection_text =text [:1000 ]
    return camera 
