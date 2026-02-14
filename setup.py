#!/usr/bin/env python3
"""Setup script for DepMapper."""

from setuptools import setup, find_packages

setup(
    name="depmapper",
    version="1.0.0",
    description="Python Dependency Mapper & Circular Import Detector",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="ATLAS (Team Brain)",
    author_email="metaphyllc@example.com",
    url="https://github.com/DonkRonk17/DepMapper",
    py_modules=["depmapper"],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "depmapper=depmapper:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
    ],
    license="MIT",
)
