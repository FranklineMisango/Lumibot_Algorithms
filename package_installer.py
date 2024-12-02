import subprocess
import sys

def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError:
        print(f"Failed to install {package}. Trying to find the nearest version...")
        package_name = package.split('==')[0]
        available_versions = subprocess.check_output([sys.executable, "-m", "pip", "index", "versions", package_name])
        available_versions = available_versions.decode('utf-8').split('\n')
        if available_versions:
            nearest_version = available_versions[1].split()[-1]
            print(f"Installing nearest version: {package_name}=={nearest_version}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package_name}=={nearest_version}"])

def main():
    with open('requirements.txt', 'r') as file:
        packages = file.readlines()
    
    for package in packages:
        package = package.strip()
        if package:
            install_package(package)

if __name__ == "__main__":
    main()