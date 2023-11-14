# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages  # type: ignore


def parse_requirements(filename, session=False):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]


install_requires = parse_requirements("requirements.txt", session=False)

setup(
    name="django-kcommunication",
    version="1.1.8",
    author=u"Tuan Bach Van",
    author_email="tuan@kajala.com",
    packages=find_packages(exclude=["project", "venv"]),
    include_package_data=True,
    url="https://github.com/kajalagroup/communication",
    license="MIT licence, see LICENCE.txt",
    description="Communication helpers and background task management for Huey queue.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    zip_safe=False,
    install_requires=install_requires,
)
