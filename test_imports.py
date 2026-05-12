import sys 
import traceback 

def test_imports ():
    modules =[
    'main',
    'ui',
    'camera_model',
    'network_utils',
    'camera_detect',
    'onvif_utils',
    'settings',
    'subnet_scan',
    'video_player',
    'ws_discovery'
    ]

    failed =[]
    for module_name in modules :
        try :
            __import__ (module_name )
            print ("[OK] Successfully imported {}".format (module_name ))
        except Exception as e :
            print ("[FAIL] Failed to import {}: {}".format (module_name ,e ))
            traceback .print_exc ()
            failed .append (module_name )

    if failed :
        print ("\nFailed modules: {}".format (", ".join (failed )))
        return False 
    else :
        print ("\nAll modules imported successfully!")
        return True 

if __name__ =="__main__":
    success =test_imports ()
    sys .exit (0 if success else 1 )