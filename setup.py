import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyperdeck",
    version="0.0.0",
    author="Daniel Flanagan",
    description="Python interface for Blackmagic Design Hyperdeck recorders.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FlantasticDan/pyperdeck",
    project_urls={
        "Bug Tracker": "https://github.com/FlantasticDan/pyperdeck/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.9",
    install_requires=[]
)
