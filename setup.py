# Example setup.py
from setuptools import setup, find_packages

setup(
    name='apple_pkr',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'PyYAML',
        'jinja2',
        # Add other dependencies as needed
    ],
    # Include additional metadata about your package
)
git init
git add .
git commit -m "first commit"
git branch -M master
git remote add origin git@github.com:CyberForgeX/pgk-rick.git
git push -u origin master