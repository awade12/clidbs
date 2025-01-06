# Python and pip commands
PYTHON := python3
PIP := $(PYTHON) -m pip

# Mark all targets as not being files
.PHONY: build clean install publish check-dist bump-patch bump-minor bump-major version

# Install development dependencies
dev-setup:
	@echo "Installing development dependencies..."
	$(PIP) install build twine

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/ build/ *.egg-info/

# Build the package
build:
	@echo "Building package..."
	$(PYTHON) -m build

# Install package locally in editable mode
install:
	@echo "Installing package locally..."
	$(PIP) install -e .

# Check distribution for PyPI compliance
check-dist:
	@echo "Checking distribution..."
	$(PYTHON) -m twine check dist/*

# Show current version
version:
	@echo "Current version:"
	@grep "__version__" src/clidbs/__init__.py

# Bump version patch (0.0.x)
bump-patch:
	@echo "Bumping patch version..."
	$(PYTHON) -c "import re; \
		content = open('src/clidbs/__init__.py').read(); \
		version = re.search('__version__ = \"(.+?)\"', content).group(1); \
		major, minor, patch = map(int, version.split('.')); \
		new_version = f'{major}.{minor}.{patch + 1}'; \
		open('src/clidbs/__init__.py', 'w').write(content.replace(version, new_version));"
	@make version

# Bump version minor (0.x.0)
bump-minor:
	@echo "Bumping minor version..."
	$(PYTHON) -c "import re; \
		content = open('src/clidbs/__init__.py').read(); \
		version = re.search('__version__ = \"(.+?)\"', content).group(1); \
		major, minor, patch = map(int, version.split('.')); \
		new_version = f'{major}.{minor + 1}.0'; \
		open('src/clidbs/__init__.py', 'w').write(content.replace(version, new_version));"
	@make version

# Bump version major (x.0.0)
bump-major:
	@echo "Bumping major version..."
	$(PYTHON) -c "import re; \
		content = open('src/clidbs/__init__.py').read(); \
		version = re.search('__version__ = \"(.+?)\"', content).group(1); \
		major, minor, patch = map(int, version.split('.')); \
		new_version = f'{major + 1}.0.0'; \
		open('src/clidbs/__init__.py', 'w').write(content.replace(version, new_version));"
	@make version

# Publish to test PyPI
test-publish: clean build check-dist
	@echo "Publishing to Test PyPI..."
	$(PYTHON) -m twine upload --repository testpypi dist/*

# Publish to production PyPI
publish: clean build check-dist
	@echo "Publishing to PyPI..."
	$(PYTHON) -m twine upload dist/*

# Quick command to bump patch version and publish
release-patch: bump-patch clean build check-dist publish
	@echo "Released new patch version to PyPI"

# Quick command to bump minor version and publish
release-minor: bump-minor clean build check-dist publish
	@echo "Released new minor version to PyPI"

# Quick command to bump major version and publish
release-major: bump-major clean build check-dist publish
	@echo "Released new major version to PyPI"

# Help command
help:
	@echo "Available commands:"
	@echo "  make dev-setup      - Install development dependencies"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make build          - Build the package"
	@echo "  make install        - Install package locally"
	@echo "  make version        - Show current version"
	@echo "  make bump-patch     - Bump patch version (0.0.X)"
	@echo "  make bump-minor     - Bump minor version (0.X.0)"
	@echo "  make bump-major     - Bump major version (X.0.0)"
	@echo "  make test-publish   - Publish to Test PyPI"
	@echo "  make publish        - Publish to PyPI"
	@echo "  make release-patch  - Bump patch version and publish"
	@echo "  make release-minor  - Bump minor version and publish"
	@echo "  make release-major  - Bump major version and publish"


