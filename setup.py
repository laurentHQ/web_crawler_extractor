from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="web_crawler_extractor",
    version="1.0.0",
    author="OpenManus",
    description="A web crawler that extracts clean content while maintaining structure",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/web_crawler_extractor",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-asyncio>=0.16.0',
            'pytest-cov>=2.12.0',
            'black>=21.0',
            'flake8>=3.9.0',
            'mypy>=0.910',
        ],
    },
    entry_points={
        'console_scripts': [
            'web-crawler=src.main:main',
        ],
    },
)