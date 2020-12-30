import setuptools

try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements

with open("README.md", "r") as fh:
    long_description = fh.read()

reqs = parse_requirements("requirements.txt", session=False)
install_requires = [str(ir.req) for ir in reqs]

setuptools.setup(
    name="notion_sync_tools",
    version="0.3.2",
    author="Egor Dmitriev",
    author_email="egordmitriev2@gmail.com",
    description="A collection of tools to sync various notion collections to markdown files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    install_requires=install_requires,
    include_package_data=True,
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={"console_scripts": ["notion-sync-tools=notion_sync_tools.__main__:main"]},
)