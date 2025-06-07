import os
import platform

def amp_relay(state, AMP_OUTPUT_PIN):
    if platform.system() == "Windows":
        print(f"Relay state: {state}")
    else:
        os.system(f"gpio mode {AMP_OUTPUT_PIN} out")
        os.system(f"gpio write {AMP_OUTPUT_PIN} {state}")
