import os
import setuptools


# recursively load package files
def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

# read long description
with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="metacerberus",
    version="0.1",
    author="Jose L. Figueroa III, Richard A. White III",
    author_email="jlfiguer@uncc.edu",
    description="Versatile Functional Ontology Assignments for Metagenomes via Hidden Markov Model (HMM) searching with environmental focus of shotgun meta'omics data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/raw-lab/metacerberus",
    scripts=['bin/meta-cerberus.py', 'bin/cerberus_setup.sh', 'bin/cerberus_slurm.sh'], # scripts to copy to 'bin' path
    packages=['meta_cerberus'],                                             # list of packages, installed to site-packages folder
    package_dir=dict(cerberus_meta='meta_cerberus'),                        # dict with 'package'='relative dir'
    package_data=dict(cerberus_data=package_files('meta_cerberus/data')),   # add non-python data to package, relative paths
    license="MIT License", # metadata
    platforms=['Unix'], # metadata
    classifiers=[ # This is the new updated way for metadata, but old way seems to still be used in some of the output
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
    python_requires='==3.7.*',
    install_requires=[
            'setuptools',
            'ray[default]',
            'metaomestats',
            'configargparse',
            'kaleido',
            'scikit-learn',
            'pandas',
            'numpy',
            'plotly',
            'psutil',
            'dominate',
            ],
)
