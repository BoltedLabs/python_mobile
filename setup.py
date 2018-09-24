from setuptools  import setup

requirements = []

with open('requirements.txt', 'r') as f:
    contents = f.read()
    requirements = contents.splitlines()

setup(
    name='Python Mobile',
    version='0.1',
    packages=['python_mobile',],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.txt').read(),
    install_requires=requirements
)
