from setuptools import find_packages, setup

setup(
    name="goproxy",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "goproxy = goproxy:run",
        ]
    },
)
