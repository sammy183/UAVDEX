import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name = "uavdex",
    author='Samuel Nassau',
    author_email='sammynassau@gmail.com',
    description='Unmanned Aerial Vehicle Design EXploration.\nA Python package for multidisciplinary analysis and optimization of electric group 1-2 UAVs.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sammy183/UAVDEX',
    project_urls={
        'Documentation':'',
        'Bug Reports':'',
        'Source Code':'',
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        # see https://pypi.org/classifiers/
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
    install_requires=["matplotlib",
                    "numpy",
                    "scipy",
                    "gekko",
                    "pandas",
                    "tqdm"],
    extras_require={
        'dev': ['check-manifest'],
        # 'test': ['coverage'],
    },
    # entry_points={
    #     'console_scripts': [  # This can provide executable scripts
    #         'run=examplepy:main',
    # You can execute `run` in bash to run `main()` in src/examplepy/__init__.py
    #     ],
    # },
)
