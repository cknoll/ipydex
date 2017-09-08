from setuptools import setup

with open("requirements.txt") as requirements_file:
    requirements = requirements_file.read()

setup(name='ipydex',
      version='0.1',
      description='IPython based debugging and exploring tool',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering',
        'Topic :: Utilities'
      ],
      keywords='ipython embedded excepthook debugger ',
      url='http://github.com/cknoll/ipydex',
      author='cknoll',
      author_email='carsten.knoll@tu-dresden.de',
      license='GPLv3+',
      install_requires=requirements,
      packages=['ipydex'],
      zip_safe=False)
