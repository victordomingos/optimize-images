# encoding: utf-8
import os
import platform
import sys

from setuptools import setup, find_packages

used = sys.version_info
required = (3, 6)

# if version of pip that doesn't understand the python_requires classifier,
# must be pip >= 9.0.0
# must be built using at least version 24.2.0 of setuptools
# in order for the python_requires argument to be recognized and the appropriate
# metadata generated
# python -m pip install --upgrade pip setuptools
if used[:2] < required:
    sys.stderr.write("Unsupported Python version: %s.%s. "
                     "Python 3.6 or later is required." % (sys.version_info.major,
                                                           sys.version_info.minor))
    sys.exit(1)

short_desc = "A command-line interface (CLI) utility written in pure Python " \
             "to help you reduce the file size of images."


def read_readme(file_name):
    with open(os.path.join(os.path.dirname(__file__), file_name)) as f:
        return f.read()

def get_requirements():
    install_requirements=['piexif>=1.1.3']
    device = platform.machine() 

    if device.startswith('iPad') or device.startswith('iPhone'):
        return install_requirements

    install_requirements.append('Pillow>=8.2.0')
    install_requirements.append('watchdog>=2.1.2')
    return install_requirements
        

setup(name='optimize-images',
      version=__import__('optimize_images').__version__,
      description=short_desc,
      author="Victor Domingos",
      packages=find_packages(),
      include_package_data=False,
      long_description=read_readme('README.md'),  # for PyPI
      long_description_content_type="text/markdown",
      license='MIT',
      url='https://no-title.victordomingos.com/projects/optimize-images/',
      project_urls={
          'Documentation': 'https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md',
          'Source': 'https://github.com/victordomingos/optimize-images',
          'Bug Reports': 'https://github.com/victordomingos/optimize-images/issues',
      },
      python_requires='>=3.7',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Information Technology',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Operating System :: iOS',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: Unix',
          'Operating System :: POSIX :: Linux ',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Topic :: Utilities',
          'Topic :: Multimedia :: Graphics',
          'Topic :: Multimedia :: Graphics :: Graphics Conversion',
      ],

      keywords='python3 pythonista-ios pil pillow image-processing ' \
               'image-compression image-optimization image-optimisation seo '
               'seo-optimization website-performance cli recursive non-recursive',

      install_requires=get_requirements(),

      entry_points={
          'console_scripts': ['optimize-images = optimize_images.__main__:main']
      },
      )
