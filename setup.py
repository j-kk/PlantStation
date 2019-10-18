from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

requirements = ["gpiozero>=1.5.1", "lockfile>=0.12.2", "python-daemon>=2.2.3", "python-dateutil>=2.8.0"]

setup(
    name="PlantStation",
    version="0.1.0",
    author="Jakub Kowalski",
    author_email="k_jakub@icloud.com",
    description="A little daemon to keep plants watered with Raspberry Pi",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/j-kk/PlantStation/",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta"
        "Environment :: No Input/Output (Daemon)"
        "Environment :: Console"
        "License :: OSI Approved :: MIT License"
        "Operating System :: POSIX :: Linux"
        "Programming Language :: Python :: 3.6"
        "Programming Language :: Python :: 3.7"
        "Programming Language :: Python :: 3.8",
    ],
)