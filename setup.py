from setuptools import setup, find_packages

setup(
    name="lora-gps-tracker",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyserial",
        "pycryptodome",
    ],
    python_requires=">=3.6",
) 