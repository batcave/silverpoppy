from setuptools import setup, find_packages

setup(
    name='silverpoppy',
    version='0.6.0',
    description='Minimalist Silverpop Engage API library.',
    long_description=(open('README.md').read()),
    url='https://github.com/kevinwaddle/silverpoppy',
    license='MIT',
    author='Kevin Waddle',
    author_email='kevin.waddle@gmail.com',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
