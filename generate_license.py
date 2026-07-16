from license_manager import get_hardware_id

hwid = get_hardware_id()

with open("license.key", "w") as file:
    file.write("HWID=" + hwid)

print("Licence créée avec succès")
print("HWID :", hwid)