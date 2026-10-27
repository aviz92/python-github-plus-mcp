# Dependency names to always skip, regardless of where they're declared.
IGNORE_DEPENDENCIES: list[str] = [
    "wheel",
    "setuptools",
]

# If True, dependencies declared without a version specifier (e.g. "requests")
# are skipped instead of checked against PyPI.
IGNORE_NONE_VERSION: bool = True
# IGNORE_NONE_VERSION: bool = False
