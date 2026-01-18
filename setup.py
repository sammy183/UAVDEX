from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="uavdex",
    version="0.1.0",   # REQUIRED — missing version breaks builds
    author="Samuel Nassau",
    author_email="sammynassau@gmail.com",
    description="Unmanned Aerial Vehicle Design EXploration.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sammy183/UAVDEX",
    project_urls={
        "Source Code": "https://github.com/sammy183/UAVDEX",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "matplotlib",
        "numpy",
        "scipy",
        "gekko",
        "pandas",
        "tqdm",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
