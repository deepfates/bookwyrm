from setuptools import setup, find_packages # type: ignore

# Read the requirements from the requirements.txt file
with open('requirements.txt', encoding='utf-8') as f:
    requirements = f.read().splitlines()

setup(
    name="bookwyrm",
    version="0.2.0",
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
)
