
from setuptools import setup, find_packages

setup(
    name="forex-multi-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.3",
        "pandas>=2.0.2",
        "matplotlib>=3.7.1",
        "scikit-learn>=1.3.0",
        "statsmodels>=0.14.0",
        "python-ta>=1.0.0",
        "aiohttp>=3.8.5",
        "websockets==10.3",
        "pymongo>=4.4.1",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "pydantic>=2.1.1",
        "tabulate>=0.9.0",
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.1",
        "black>=23.7.0",
        "flake8>=6.1.0",
        "aiolimiter>=1.1.0",
        "httpx>=0.24.1",
        "joblib>=1.3.1",
        "cryptography>=41.0.3",
        "websocket-client>=1.5.0",
        "simplejson>=3.17.6",
    ],
    dependency_links=[
        "git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api"
    ],
)
