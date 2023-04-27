from setuptools import setup, find_packages
import sys, os

version = '0.0.2'

setup(name='citehound',
      version=version,
      description="A platform that enables systematic research over bibliographic data sources.",
      long_description="",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='scientometrics bibliography research review',
      author='Athanasios Anastasiou',
      author_email='athanastasiou@gmail.com',
      scripts=["scripts/cadmin.py", 
               "scripts/cmeshprep.py",],
      packages=["citehound", ],
      include_package_data=True,
      zip_safe=True,
      install_requires=["pygraphviz", "networkx", "neomodel", "lxml", "click", "matplotlib", "pyyaml"],
      # entry_points=""
      )
