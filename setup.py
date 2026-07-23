from setuptools import setup, find_packages

setup(
    name="ai-control-plane",
    version="1.0.0",
    description="Enterprise AI Gateway with SA-specific PII detection, policy enforcement, and audit logging",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.3",
        "pydantic-settings>=2.1.0",
        "presidio-analyzer>=2.2.353",
        "presidio-anonymizer>=2.2.353",
        "spacy>=3.7.2",
        "httpx>=0.26.0",
        "redis>=5.0.1",
        "asyncpg>=0.29.0",
    ],
    entry_points={
        "console_scripts": [
            "ai-control-plane=src.main:app",
        ],
    },
)
