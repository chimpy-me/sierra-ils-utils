from setuptools import setup, find_packages

setup(
    name="sierra-ils-utils",
    version="0.0.1a20231213",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.25.2,<0.26.0",
        "pydantic>=1.10.13,<2.0.0",
        "pymarc>=5.1.0,<6.0.0",
    ],
    author="Ray Voelker",
    author_email="ray.voelker@gmail.com",
    description="Python wrappers for working with the Sierra ILS",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chimpy-me/sierra-ils-utils/",
    license="MIT",
)
