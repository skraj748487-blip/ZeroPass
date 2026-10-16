from setuptools import setup, find_packages

setup(
    name="ghostkey-core",
    version="1.0.0",
    author="Sahil Ahmad",
    description="Decentralized Zero-Knowledge Hardware-Bound Biometric Identity Protocol",
    long_description=open("README.md").read() if open("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/skraj748487-blip/ZeroPass",
    py_modules=["core_engine", "node_daemon", "node_client", "gossip_engine"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
    ],
    python_requires=">=3.8",
)
