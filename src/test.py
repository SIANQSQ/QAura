from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import warnings

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

def get_friendly_name(dev) -> str:
    with warnings.catch_warnings():
        # suppress deprecation warning for GetAllDevices
        warnings.simplefilter("ignore", UserWarning)
        
        # get the unique endpoint ID
        dev_id = dev.GetId()
        
        # AudioUtilities.GetAllDevices() yields AudioDevice wrappers
        for d in AudioUtilities.GetAllDevices():
            if d.id == dev_id:
                return d.FriendlyName
        return "Unknown Device"

def main():
    device = AudioUtilities.GetSpeakers()
    name = get_friendly_name(device)
    print(f"Device found: {name}")
    
    # now get the endpoint-volume interface
    interface = device.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    
    print("Muted?:", "Yes" if volume.GetMute() else "No")
    print("Level (dB):", volume.GetMasterVolumeLevel())
    print("Range (dB):", volume.GetVolumeRange())
    
    print("Setting to -20 dB…")
    volume.SetMasterVolumeLevel(-20.0, None)
    print("New level:", volume.GetMasterVolumeLevel())

if __name__ == "__main__":
    main()