from setuptools import setup, find_packages


def get_readme(name="README.md"):
    with open(name) as f:
        return f.read()


requirements = ["redis", "qtpy", "PyQt5", "msgpack", "msgpack-numpy"]


setup(
    name="qredis",
    version="1.1.0",
    description="Qt based Redis GUI",
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    author="Tiago Coutinho",
    author_email="coutinhotiago@gmail.com",
    url="https://github.com/tiagocoutinho/qredis",
    packages=find_packages(),
    package_data={"qredis.images": ["*.png"], "qredis.ui": ["*.ui"], "qredis_web": ["templates/*.html", "static/*"]},
    entry_points={"console_scripts": ["qredis=qredis.window:main", "qredis-web=qredis_web.app:main"]},
    install_requires=requirements,
    extras_require={
        "web": [
            "fastapi>=0.110; python_version>='3.8'",
            "uvicorn[standard]>=0.23; python_version>='3.8'",
            "hypercorn>=0.15; python_version>='3.8'",
            "jinja2>=3; python_version>='3.8'",
        ]
    },
    keywords="redis,GUI,Qt",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.5",
)
