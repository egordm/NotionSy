import setuptools
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    dependency_links=[
        "git+https://github.com/EgorDm/md2notion.git@c7f2b9754cf06858e71af0c7bb36168fe20f030d#egg=md2notion",
        "git+https://github.com/EgorDm/notion-py.git@faa9ee8d86ae8ea79757ff72c78fad618c8b811c#egg=notion",
    ],
    name="notionsy",
    version="0.3.2",
    author="Egor Dmitriev",
    author_email="egordmitriev2@gmail.com",
    description="A collection of tools to sync various notion collections to markdown files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    install_requires=[
        "beautifulsoup4==4.9.3",
        "bs4==0.0.1",
        "cached-property==1.5.2",
        "certifi==2020.12.5",
        "chardet==4.0.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "click==7.1.2",
        "click-config-file==0.6.0",
        "commonmark==0.9.1",
        "configobj==5.0.6",
        "dictdiffer==0.8.1",
        "idna==2.10; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "injector==0.18.4",
        "mistletoe==0.7.2; python_version ~= '3.3'",
        "notion2md==1.2.3.1",
        "python-slugify==4.0.1",
        "pytz==2020.5",
        "pyyaml==5.3.1",
        "requests==2.25.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "six==1.15.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "soupsieve==2.1; python_version >= '3.0'",
        "text-unidecode==1.3",
        "tqdm==4.55.1",
        "typing-extensions==3.7.4.3; python_version < '3.9'",
        "tzlocal==2.1",
        "urllib3==1.26.2",
    ],
    include_package_data=True,
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["notionsy=notionsy.__main__:cli"]},
)
