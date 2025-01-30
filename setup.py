from setuptools import setup, find_packages

setup(
    name="sierra-ils-utils",
    version="0.0.1a20250130",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.28.0,<0.29.0",
        "pymarc>=5.2.0,<6.0.0",
    ],
    extras_require={
        "test": ["pytest>=8.3.4","pytest-asyncio>=0.25.0","respx>=0.22.0"],
    },
    author="Ray Voelker",
    author_email="ray.voelker@gmail.com",
    description="Python wrappers for working with the Sierra ILS",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chimpy-me/sierra-ils-utils/",
    license="MIT",
)
