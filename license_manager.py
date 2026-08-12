import subprocess
import hashlib
import os
import sys


def _chemin_license() -> str:
    if getattr(sys, "frozen", False):
        dossier = os.path.dirname(sys.executable)
    else:
        dossier = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dossier, "license.key")


def get_hardware_id():

    try:
        uuid = subprocess.check_output(
            [
                "powershell",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystemProduct).UUID"
            ],
            text=True
        ).strip()


        disk = subprocess.check_output(
            [
                "powershell",
                "-Command",
                "(Get-CimInstance Win32_DiskDrive | Select-Object -First 1).SerialNumber"
            ],
            text=True
        ).strip()


        hardware_data = uuid + disk

        hwid = hashlib.sha256(
            hardware_data.encode()
        ).hexdigest()

        return hwid


    except Exception as e:
        print("Erreur récupération HWID :", e)
        return None



def check_license():

    current_hwid = get_hardware_id()

    if current_hwid is None:
        return False


    chemin = _chemin_license()

    if not os.path.exists(chemin):
        print("license.key introuvable :", chemin)
        return False

    with open(chemin, "r") as file:
        licensed_hwid = file.read().replace("HWID=", "").strip()


    return current_hwid == licensed_hwid