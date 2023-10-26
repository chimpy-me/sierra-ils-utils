from setuptools import setup, find_packages

setup(
    name="sierra-ils-utils",
    version="0.0.1a20231026",
    packages=find_packages(),
    install_requires=[
        "psycopg2-binary==2.9.9",
        "requests==2.31.0",
        "pydantic==2.4.2",
    ],
    author="Ray Voelker",
    author_email="ray.voelker@gmail.com",
    description="Python wrappers for working with the Sierra ILS",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chimpy-me/sierra-ils-utils/",
    license="MIT",
)