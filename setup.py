import pathlib
import re
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

init_file = (HERE / "avcord/__init__.py").read_text()

re_version = r'__version__ = \"([0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3})\"'
_version = re.search(re_version, init_file)

if _version is None:
  raise RuntimeError("Version is not set")

version = _version.group(1)

# Read description
re_description = r'__description__ = \"(.{1,})\"'
_description = re.search(re_description, init_file)

if _description is None:
  raise RuntimeError("Description is not set")

description = _description.group(1)

# Read type license
re_license = r'__license__ = \"(.{1,})\"'
_license = re.search(re_license, init_file)

if _license is None:
  raise RuntimeError("license is not set")

type_license = _license.group(1)

requirements = []
with open('./requirements.txt', 'r') as r:
  requirements = r.read().splitlines()

requirements_docs = []
with open('./requirements-docs.txt', 'r') as r:
  requirements_docs = r.read().splitlines()

extras_require = {
  'docs': requirements_docs
}

packages = find_packages('.')

setup(
  name = 'av-discord',         
  packages = packages,   
  version = version,
  license=type_license,     
  description = description,
  long_description= README,
  long_description_content_type= 'text/markdown',
  author = 'Rahman Yusuf',              
  author_email = 'danipart4@gmail.com',
  url = 'https://github.com/mansuf/av-cord',  
  keywords = ['discord', 'audio'], 
  install_requires=requirements,
  extras_require=extras_require,
  classifiers=[
    'Development Status :: 4 - Beta',  
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',  
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10'
  ],
  python_requires='>=3.8'
)
