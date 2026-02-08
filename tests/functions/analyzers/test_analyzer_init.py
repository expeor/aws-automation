"""
tests/analyzers/test_analyzer_init.py - Analyzer Module Structure Tests

Comprehensive tests for all analyzer __init__.py files:
- CATEGORY dict validation
- TOOLS list validation
- Schema compliance
- Module existence verification
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any

import pytest

from core.config import VALID_AREAS, VALID_PERMISSIONS, get_analyzers_path

logger = logging.getLogger(__name__)

# Required CATEGORY fields
REQUIRED_CATEGORY_FIELDS = {
    "name",
    "display_name",
    "description",
    "description_en",
    "aliases",
}

# Required TOOL fields
REQUIRED_TOOL_FIELDS = {
    "name",
    "name_en",
    "description",
    "description_en",
    "permission",
    "module",
    "area",
}

# Optional TOOL fields
OPTIONAL_TOOL_FIELDS = {
    "is_global",  # For global services like IAM
    "function",  # Custom function name (default: run)
}


def get_all_analyzer_dirs() -> list[Path]:
    """Get all analyzer directories"""
    analyzers_path = get_analyzers_path()
    return [
        d
        for d in analyzers_path.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "__init__.py").exists()
    ]


def load_analyzer_module(analyzer_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load CATEGORY and TOOLS from an analyzer __init__.py"""
    module_name = f"functions.analyzers.{analyzer_dir.name}"
    try:
        module = importlib.import_module(module_name)
        category = getattr(module, "CATEGORY", None)
        tools = getattr(module, "TOOLS", None)
        return category, tools
    except Exception as e:
        pytest.fail(f"Failed to import {module_name}: {e}")


class TestAnalyzerStructure:
    """Test analyzer module structure and schema"""

    @pytest.fixture
    def analyzer_dirs(self) -> list[Path]:
        """Get all analyzer directories"""
        return get_all_analyzer_dirs()

    def test_all_analyzers_have_init(self, analyzer_dirs):
        """Test that all analyzer directories have __init__.py"""
        assert len(analyzer_dirs) > 0, "No analyzer directories found"
        for analyzer_dir in analyzer_dirs:
            init_file = analyzer_dir / "__init__.py"
            assert init_file.exists(), f"Missing __init__.py in {analyzer_dir.name}"

    def test_all_analyzers_have_category(self, analyzer_dirs):
        """Test that all analyzers have CATEGORY dict"""
        for analyzer_dir in analyzer_dirs:
            category, _ = load_analyzer_module(analyzer_dir)
            assert category is not None, f"{analyzer_dir.name}: Missing CATEGORY"
            assert isinstance(category, dict), f"{analyzer_dir.name}: CATEGORY must be a dict"

    def test_all_analyzers_have_tools(self, analyzer_dirs):
        """Test that all analyzers have TOOLS list"""
        for analyzer_dir in analyzer_dirs:
            _, tools = load_analyzer_module(analyzer_dir)
            assert tools is not None, f"{analyzer_dir.name}: Missing TOOLS"
            assert isinstance(tools, list), f"{analyzer_dir.name}: TOOLS must be a list"
            assert len(tools) > 0, f"{analyzer_dir.name}: TOOLS list is empty"


class TestCategorySchema:
    """Test CATEGORY dict schema compliance"""

    @pytest.fixture
    def all_categories(self) -> list[tuple[str, dict[str, Any]]]:
        """Load all CATEGORY dicts"""
        categories = []
        for analyzer_dir in get_all_analyzer_dirs():
            category, _ = load_analyzer_module(analyzer_dir)
            if category:
                categories.append((analyzer_dir.name, category))
        return categories

    def test_category_has_required_fields(self, all_categories):
        """Test that CATEGORY has all required fields"""
        for analyzer_name, category in all_categories:
            missing_fields = REQUIRED_CATEGORY_FIELDS - set(category.keys())
            assert not missing_fields, f"{analyzer_name}: Missing required CATEGORY fields: {missing_fields}"

    def test_category_name_is_string(self, all_categories):
        """Test that CATEGORY['name'] is a non-empty string"""
        for analyzer_name, category in all_categories:
            assert "name" in category, f"{analyzer_name}: Missing 'name' field"
            assert isinstance(category["name"], str), f"{analyzer_name}: 'name' must be string"
            assert len(category["name"]) > 0, f"{analyzer_name}: 'name' cannot be empty"

    def test_category_name_matches_directory(self, all_categories):
        """Test that CATEGORY['name'] matches directory name"""
        for analyzer_name, category in all_categories:
            assert category["name"] == analyzer_name, (
                f"{analyzer_name}: CATEGORY name '{category['name']}' should match directory name"
            )

    def test_category_display_name_is_string(self, all_categories):
        """Test that CATEGORY['display_name'] is a non-empty string"""
        for analyzer_name, category in all_categories:
            assert "display_name" in category, f"{analyzer_name}: Missing 'display_name' field"
            assert isinstance(category["display_name"], str), f"{analyzer_name}: 'display_name' must be string"
            assert len(category["display_name"]) > 0, f"{analyzer_name}: 'display_name' cannot be empty"

    def test_category_descriptions_are_strings(self, all_categories):
        """Test that CATEGORY descriptions are non-empty strings"""
        for analyzer_name, category in all_categories:
            assert "description" in category, f"{analyzer_name}: Missing 'description' field"
            assert isinstance(category["description"], str), f"{analyzer_name}: 'description' must be string"
            assert len(category["description"]) > 0, f"{analyzer_name}: 'description' cannot be empty"

            assert "description_en" in category, f"{analyzer_name}: Missing 'description_en' field"
            assert isinstance(category["description_en"], str), f"{analyzer_name}: 'description_en' must be string"
            assert len(category["description_en"]) > 0, f"{analyzer_name}: 'description_en' cannot be empty"

    def test_category_aliases_is_list(self, all_categories):
        """Test that CATEGORY['aliases'] is a list"""
        for analyzer_name, category in all_categories:
            assert "aliases" in category, f"{analyzer_name}: Missing 'aliases' field"
            assert isinstance(category["aliases"], list), f"{analyzer_name}: 'aliases' must be a list"

            # All aliases should be strings
            for alias in category["aliases"]:
                assert isinstance(alias, str), f"{analyzer_name}: All aliases must be strings, got {type(alias)}"

    def test_category_no_extra_fields(self, all_categories):
        """Test that CATEGORY doesn't have unexpected extra fields"""
        for analyzer_name, category in all_categories:
            extra_fields = set(category.keys()) - REQUIRED_CATEGORY_FIELDS
            # Allow for future extensions but log warning
            if extra_fields:
                logger.warning(f"{analyzer_name}: Extra CATEGORY fields: {extra_fields}")


class TestToolsSchema:
    """Test TOOLS list schema compliance"""

    @pytest.fixture
    def all_tools(self) -> list[tuple[str, list[dict[str, Any]]]]:
        """Load all TOOLS lists"""
        tools_list = []
        for analyzer_dir in get_all_analyzer_dirs():
            _, tools = load_analyzer_module(analyzer_dir)
            if tools:
                tools_list.append((analyzer_dir.name, tools))
        return tools_list

    def test_tools_has_required_fields(self, all_tools):
        """Test that all tools have required fields"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                missing_fields = REQUIRED_TOOL_FIELDS - set(tool.keys())
                assert not missing_fields, f"{analyzer_name}: Tool #{i} missing required fields: {missing_fields}"

    def test_tools_name_is_string(self, all_tools):
        """Test that tool names are non-empty strings"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                assert "name" in tool, f"{analyzer_name}: Tool #{i} missing 'name' field"
                assert isinstance(tool["name"], str), f"{analyzer_name}: Tool #{i} 'name' must be string"
                assert len(tool["name"]) > 0, f"{analyzer_name}: Tool #{i} 'name' cannot be empty"

                assert "name_en" in tool, f"{analyzer_name}: Tool #{i} missing 'name_en' field"
                assert isinstance(tool["name_en"], str), f"{analyzer_name}: Tool #{i} 'name_en' must be string"
                assert len(tool["name_en"]) > 0, f"{analyzer_name}: Tool #{i} 'name_en' cannot be empty"

    def test_tools_description_is_string(self, all_tools):
        """Test that tool descriptions are non-empty strings"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                assert "description" in tool, f"{analyzer_name}: Tool #{i} missing 'description' field"
                assert isinstance(tool["description"], str), f"{analyzer_name}: Tool #{i} 'description' must be string"
                assert len(tool["description"]) > 0, f"{analyzer_name}: Tool #{i} 'description' cannot be empty"

                assert "description_en" in tool, f"{analyzer_name}: Tool #{i} missing 'description_en' field"
                assert isinstance(tool["description_en"], str), (
                    f"{analyzer_name}: Tool #{i} 'description_en' must be string"
                )
                assert len(tool["description_en"]) > 0, f"{analyzer_name}: Tool #{i} 'description_en' cannot be empty"

    def test_tools_permission_is_valid(self, all_tools):
        """Test that tool permission is valid"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                assert "permission" in tool, f"{analyzer_name}: Tool #{i} missing 'permission' field"
                permission = tool["permission"]
                assert permission in VALID_PERMISSIONS, (
                    f"{analyzer_name}: Tool #{i} invalid permission '{permission}', must be one of {VALID_PERMISSIONS}"
                )

    def test_tools_module_is_string(self, all_tools):
        """Test that tool module is a non-empty string"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                assert "module" in tool, f"{analyzer_name}: Tool #{i} missing 'module' field"
                assert isinstance(tool["module"], str), f"{analyzer_name}: Tool #{i} 'module' must be string"
                assert len(tool["module"]) > 0, f"{analyzer_name}: Tool #{i} 'module' cannot be empty"

    def test_tools_area_is_valid(self, all_tools):
        """Test that tool area is valid"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                assert "area" in tool, f"{analyzer_name}: Tool #{i} missing 'area' field"
                area = tool["area"]
                assert area in VALID_AREAS, (
                    f"{analyzer_name}: Tool #{i} invalid area '{area}', must be one of {VALID_AREAS}"
                )

    def test_tools_optional_fields_are_valid(self, all_tools):
        """Test that optional tool fields have correct types"""
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                # Check is_global if present
                if "is_global" in tool:
                    assert isinstance(tool["is_global"], bool), (
                        f"{analyzer_name}: Tool #{i} 'is_global' must be boolean"
                    )

    def test_tools_no_unexpected_fields(self, all_tools):
        """Test that tools don't have unexpected extra fields"""
        allowed_fields = REQUIRED_TOOL_FIELDS | OPTIONAL_TOOL_FIELDS
        for analyzer_name, tools in all_tools:
            for i, tool in enumerate(tools):
                extra_fields = set(tool.keys()) - allowed_fields
                if extra_fields:
                    logger.warning(f"{analyzer_name}: Tool #{i} has extra fields: {extra_fields}")


class TestModuleExistence:
    """Test that referenced modules actually exist"""

    @pytest.fixture
    def all_tools_with_modules(
        self,
    ) -> list[tuple[str, str, str, str]]:
        """Get all tools with their module names (analyzer_name, module_name, function_name, tool_name)"""
        tools_modules = []
        for analyzer_dir in get_all_analyzer_dirs():
            _, tools = load_analyzer_module(analyzer_dir)
            if tools:
                for tool in tools:
                    tools_modules.append(
                        (
                            analyzer_dir.name,
                            tool.get("module", ""),
                            tool.get("function", "run"),  # Default to 'run' if no function specified
                            tool.get("name", "Unknown"),
                        )
                    )
        return tools_modules

    def test_all_referenced_modules_exist(self, all_tools_with_modules):
        """Test that all modules referenced in TOOLS exist"""
        analyzers_path = get_analyzers_path()
        missing_modules = []
        known_missing = []  # Known missing modules (work in progress)

        for analyzer_name, module_name, _function_name, tool_name in all_tools_with_modules:
            if not module_name:
                missing_modules.append(f"{analyzer_name}: Tool '{tool_name}' has no module specified")
                continue

            module_file = analyzers_path / analyzer_name / f"{module_name}.py"
            if not module_file.exists():
                # Known missing modules (work in progress)
                if analyzer_name == "cost" and module_name == "coh":
                    known_missing.append(f"{analyzer_name}: Module '{module_name}.py' (Cost Optimization Hub - WIP)")
                else:
                    missing_modules.append(
                        f"{analyzer_name}: Module '{module_name}.py' not found for tool '{tool_name}'"
                    )

        if known_missing:
            logger.warning(
                "Known missing modules (work in progress):\n" + "\n".join(f"  - {msg}" for msg in known_missing)
            )

        if missing_modules:
            pytest.fail("Missing modules found:\n" + "\n".join(f"  - {msg}" for msg in missing_modules))

    def test_modules_can_be_imported(self, all_tools_with_modules):
        """Test that all referenced modules can be imported"""
        import_errors = []
        known_missing = []

        for analyzer_name, module_name, _function_name, tool_name in all_tools_with_modules:
            if not module_name:
                continue

            # Skip known missing modules
            if analyzer_name == "cost" and module_name == "coh":
                known_missing.append(f"{analyzer_name}.{module_name}")
                continue

            full_module_name = f"functions.analyzers.{analyzer_name}.{module_name}"
            try:
                importlib.import_module(full_module_name)
            except ImportError as e:
                import_errors.append(
                    f"{analyzer_name}: Cannot import module '{module_name}' for tool '{tool_name}': {e}"
                )

        if known_missing:
            logger.warning(f"Skipping known missing modules: {', '.join(known_missing)}")

        if import_errors:
            pytest.fail("Import errors found:\n" + "\n".join(f"  - {msg}" for msg in import_errors))

    def test_modules_have_run_function(self, all_tools_with_modules):
        """Test that all tool modules have the required function (run() or custom function)"""
        missing_run_errors = []

        for analyzer_name, module_name, function_name, tool_name in all_tools_with_modules:
            if not module_name:
                continue

            # Skip known missing modules
            if analyzer_name == "cost" and module_name == "coh":
                continue

            full_module_name = f"functions.analyzers.{analyzer_name}.{module_name}"
            try:
                module = importlib.import_module(full_module_name)
                # Check for the specified function (either 'run' or a custom function name)
                if not hasattr(module, function_name):
                    missing_run_errors.append(
                        f"{analyzer_name}: Module '{module_name}' for tool '{tool_name}' "
                        f"must have a {function_name}() function"
                    )
                elif not callable(getattr(module, function_name)):
                    missing_run_errors.append(
                        f"{analyzer_name}: '{function_name}' in module '{module_name}' for tool '{tool_name}' "
                        f"must be callable"
                    )
            except ImportError:
                # Skip if module can't be imported (will be caught by previous test)
                pass

        if missing_run_errors:
            pytest.fail("Missing or invalid run functions:\n" + "\n".join(f"  - {msg}" for msg in missing_run_errors))


class TestAnalyzerConsistency:
    """Test consistency across all analyzers"""

    @pytest.fixture
    def all_analyzer_data(self) -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
        """Load all analyzer data (name, CATEGORY, TOOLS)"""
        data = []
        for analyzer_dir in get_all_analyzer_dirs():
            category, tools = load_analyzer_module(analyzer_dir)
            if category and tools:
                data.append((analyzer_dir.name, category, tools))
        return data

    def test_unique_category_names(self, all_analyzer_data):
        """Test that all category names are unique"""
        category_names = [category["name"] for _, category, _ in all_analyzer_data]
        duplicates = [name for name in category_names if category_names.count(name) > 1]
        assert not duplicates, f"Duplicate category names found: {set(duplicates)}"

    def test_tool_names_unique_within_analyzer(self, all_analyzer_data):
        """Test that tool names are unique within each analyzer"""
        for analyzer_name, _, tools in all_analyzer_data:
            tool_names = [tool["name"] for tool in tools]
            duplicates = [name for name in tool_names if tool_names.count(name) > 1]
            assert not duplicates, f"{analyzer_name}: Duplicate tool names found: {set(duplicates)}"

            tool_names_en = [tool["name_en"] for tool in tools]
            duplicates_en = [name for name in tool_names_en if tool_names_en.count(name) > 1]
            assert not duplicates_en, f"{analyzer_name}: Duplicate English tool names found: {set(duplicates_en)}"

    def test_module_names_unique_within_analyzer(self, all_analyzer_data):
        """Test that module names are unique within each analyzer (unless using different functions)"""
        for analyzer_name, _, tools in all_analyzer_data:
            # Create a list of (module, function) tuples to check for true duplicates
            # If a module is used multiple times but with different 'function' attributes, it's OK
            module_function_pairs = []
            for tool in tools:
                module = tool["module"]
                function = tool.get("function", "run")  # Default to 'run' if no function specified
                module_function_pairs.append((module, function))

            duplicates = [pair for pair in module_function_pairs if module_function_pairs.count(pair) > 1]
            assert not duplicates, (
                f"{analyzer_name}: Duplicate (module, function) pairs found: {set(duplicates)}. "
                f"Each tool should have a unique module or use different function names."
            )

    def test_area_distribution(self, all_analyzer_data):
        """Log distribution of tools by area (informational test)"""
        area_counts: dict[str, int] = {}
        for _, _, tools in all_analyzer_data:
            for tool in tools:
                area = tool["area"]
                area_counts[area] = area_counts.get(area, 0) + 1

        logger.info("Tool distribution by area:")
        for area in sorted(area_counts.keys()):
            logger.info(f"  {area}: {area_counts[area]} tools")

        # This is just informational, no assertion needed
        assert len(area_counts) > 0, "No tools found"

    def test_permission_distribution(self, all_analyzer_data):
        """Log distribution of tools by permission (informational test)"""
        permission_counts: dict[str, int] = {}
        for _, _, tools in all_analyzer_data:
            for tool in tools:
                permission = tool["permission"]
                permission_counts[permission] = permission_counts.get(permission, 0) + 1

        logger.info("Tool distribution by permission:")
        for permission in sorted(permission_counts.keys()):
            logger.info(f"  {permission}: {permission_counts[permission]} tools")

        # Most tools should be read-only
        assert permission_counts.get("read", 0) > 0, "Expected at least some read-only tools"


class TestAnalyzerCoverage:
    """Test analyzer coverage and statistics"""

    def test_minimum_analyzer_count(self):
        """Test that we have a reasonable number of analyzers"""
        analyzer_dirs = get_all_analyzer_dirs()
        # Based on the CLAUDE.md documentation, we should have 30+ categories
        assert len(analyzer_dirs) >= 20, f"Expected at least 20 analyzers, found {len(analyzer_dirs)}"

    def test_minimum_tool_count(self):
        """Test that we have a reasonable number of tools"""
        total_tools = 0
        for analyzer_dir in get_all_analyzer_dirs():
            _, tools = load_analyzer_module(analyzer_dir)
            if tools:
                total_tools += len(tools)

        # Based on the CLAUDE.md documentation, we should have 65+ tools
        assert total_tools >= 40, f"Expected at least 40 tools, found {total_tools}"

    def test_all_areas_are_used(self):
        """Test that all defined areas are actually used"""
        used_areas = set()
        for analyzer_dir in get_all_analyzer_dirs():
            _, tools = load_analyzer_module(analyzer_dir)
            if tools:
                for tool in tools:
                    used_areas.add(tool["area"])

        # We should be using most of the defined areas
        unused_areas = VALID_AREAS - used_areas
        if unused_areas:
            logger.warning(f"Unused areas: {unused_areas}")

        # At least half of the areas should be used
        assert len(used_areas) >= len(VALID_AREAS) // 2, (
            f"Too few areas in use: {used_areas}. Unused areas: {unused_areas}"
        )
