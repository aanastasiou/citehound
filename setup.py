from setuptools import setup, find_packages
import sys, os

version = '0.0.3'

setup(name='citehound',
      version=version,
      description="A platform that enables systematic research over bibliographic data sources.",
      long_description=open("README.rst").read(),
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Console",
                   "License :: OSI Approved :: Apple Public Source License",
                   "Operating System :: POSIX :: Linux",
                   "Programming Language :: Python :: 3",
                   "Topic :: Scientific/Engineering",
                   "Topic :: Text Processing",
                   "Topic :: Utilities"], 
      keywords='scientometrics bibliography research review',
      author='Athanasios Anastasiou',
      author_email='athanastasiou@gmail.com',
      scripts=["scripts/cadmin.py", 
               "scripts/cmeshprep.py",],
      packages=["citehound", ],
      include_package_data=True,
      zip_safe=True,
      install_requires=["pygraphviz", "networkx", "neomodel", "lxml", "click", "matplotlib", "pyyaml", "pkgutil"],
      # entry_points=""
      )
