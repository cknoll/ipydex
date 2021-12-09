
import sys
import os
import setuptools
from setuptools import setup, find_packages


packagename = "ipydex"

# consider the path of `setup.py` as root directory:
PROJECTROOT = os.path.dirname(sys.argv[0]) or "."
release_path = os.path.join(PROJECTROOT, "src", packagename, "release.py")
with open(release_path, encoding="utf8") as release_file:
    __version__ = release_file.read().split('__version__ = "', 1)[1].split('"', 1)[0]


with open("requirements.txt") as requirements_file:
    requirements = requirements_file.read()

setup(
    name=packagename,
    version=__version__,
    author="Carsten Knoll",
    author_email="firstname.lastname@posteo.de",
    packages=find_packages("src"),
    package_dir={"": "src"},
    url='http://github.com/cknoll/ipydex',
    license="GPLv3+",
    description='IPython based debugging and exploring tool',
    long_description="""
# IPython based debugging and exploring tool

This package provides the following features:

- `IPS()` – An embedded IPython shell with some extra features like conditional execution: `IPS(x>0)`.
- `activate_ips_on_exception()` – Open an IPython shell in the frame where an exception is raised, but with the ability to move to other frames.
- `dirsearch` – easily search for substrings in the attribute list of an object or in the keys of a dict.
- `displaytools` – an extesion for jupyter notebooks to display intermediate results (e.g. of assignments). Useful for didactic purposes.
""",
    long_description_content_type="text/markdown",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
    ],
    keywords='ipython embedded excepthook debugger ',
    zip_safe=False,
)




