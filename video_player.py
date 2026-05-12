import os 
import time 
import cv2 
from PySide6 .QtCore import QObject ,QThread ,Signal ,Qt 
from PySide6 .QtGui import QImage ,QPixmap 
from PySide6 .QtWidgets import QLabel ,QVBoxLayout ,QWidget 


class StreamWorker (QObject ):
    frame_ready =Signal (QImage )
    status =Signal (str )
    error =Signal (str )
    finished =Signal ()

    def __init__ (self ,rtsp_url :str ):
        super ().__init__ ()
        self .rtsp_url =rtsp_url 
        self .running =False 

    def start (self ):
        self .running =True 
        os .environ .setdefault ("OPENCV_FFMPEG_CAPTURE_OPTIONS","rtsp_transport;tcp|stimeout;5000000")
        while self .running :
            self .status .emit ("Подключение к потоку...")
            cap =cv2 .VideoCapture (self .rtsp_url ,cv2 .CAP_FFMPEG )
            if not cap .isOpened ():
                self .error .emit ("Не удалось открыть RTSP-поток")
                cap .release ()
                time .sleep (2 )
                continue 
            self .status .emit ("Поток открыт")
            while self .running :
                ok ,frame =cap .read ()
                if not ok or frame is None :
                    self .error .emit ("Поток прерван, пробую подключиться заново")
                    break 
                rgb =cv2 .cvtColor (frame ,cv2 .COLOR_BGR2RGB )
                height ,width ,channels =rgb .shape 
                image =QImage (rgb .data ,width ,height ,channels *width ,QImage .Format_RGB888 ).copy ()
                self .frame_ready .emit (image )
            cap .release ()
            if self .running :
                time .sleep (1 )
        self .finished .emit ()

    def stop (self ):
        self .running =False 


class VideoWindow (QWidget ):
    def __init__ (self ,rtsp_url :str ):
        super ().__init__ ()
        self .setWindowTitle ("IP Camera Viewer")
        self .resize (960 ,600 )
        self .video_label =QLabel ("Ожидание видео...")
        self .video_label .setAlignment (Qt .AlignCenter )
        self .video_label .setMinimumSize (640 ,360 )
        self .status_label =QLabel (rtsp_url )
        layout =QVBoxLayout ()
        layout .addWidget (self .video_label )
        layout .addWidget (self .status_label )
        self .setLayout (layout )
        self .thread =QThread (self )
        self .worker =StreamWorker (rtsp_url )
        self .worker .moveToThread (self .thread )
        self .thread .started .connect (self .worker .start )
        self .worker .frame_ready .connect (self .update_frame )
        self .worker .status .connect (self .status_label .setText )
        self .worker .error .connect (self .status_label .setText )
        self .worker .finished .connect (self .thread .quit )
        self .thread .start ()

    def update_frame (self ,image :QImage ):
        pixmap =QPixmap .fromImage (image )
        scaled =pixmap .scaled (self .video_label .size (),Qt .KeepAspectRatio ,Qt .SmoothTransformation )
        self .video_label .setPixmap (scaled )

    def closeEvent (self ,event ):
        self .worker .stop ()
        self .thread .quit ()
        self .thread .wait (3000 )
        event .accept ()
