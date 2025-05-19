import os
import sys
import pytest
import argparse
import importlib
from unittest.mock import MagicMock, patch
from common.plugins import BaseImportPlugin, PluginRegistry, register_plugin


class TestBaseImportPlugin:
    """Tests for the BaseImportPlugin class."""

    def test_abstract_methods(self):
        """Test that BaseImportPlugin is an abstract class with required methods."""
        # Attempting to instantiate BaseImportPlugin should raise TypeError
        with pytest.raises(TypeError):
            BaseImportPlugin()
        
        # Check that the abstract methods are defined
        assert hasattr(BaseImportPlugin, "get_name")
        assert hasattr(BaseImportPlugin, "get_description")
        assert hasattr(BaseImportPlugin, "create_parser")
        assert hasattr(BaseImportPlugin, "convert")


class TestPluginRegistry:
    """Tests for the PluginRegistry class."""

    def setup_method(self):
        """Set up the test environment."""
        # Clear the plugin registry before each test
        PluginRegistry._plugins = {}

    def test_register_and_get_plugin(self):
        """Test registering and retrieving a plugin."""
        # Create a mock plugin class
        class MockPlugin(BaseImportPlugin):
            @classmethod
            def get_name(cls):
                return "mock"
            
            @classmethod
            def get_description(cls):
                return "Mock plugin"
            
            @classmethod
            def create_parser(cls):
                return argparse.ArgumentParser()
            
            @classmethod
            def convert(cls, args):
                pass
        
        # Register the plugin
        PluginRegistry.register(MockPlugin)
        
        # Check that the plugin was registered
        assert "mock" in PluginRegistry._plugins
        assert PluginRegistry._plugins["mock"] is MockPlugin
        
        # Check that get_plugin returns the correct plugin
        assert PluginRegistry.get_plugin("mock") is MockPlugin
        
        # Check that get_plugin returns None for unknown plugins
        assert PluginRegistry.get_plugin("unknown") is None

    def test_get_all_plugins(self):
        """Test retrieving all registered plugins."""
        # Create mock plugin classes
        class MockPlugin1(BaseImportPlugin):
            @classmethod
            def get_name(cls):
                return "mock1"
            
            @classmethod
            def get_description(cls):
                return "Mock plugin 1"
            
            @classmethod
            def create_parser(cls):
                return argparse.ArgumentParser()
            
            @classmethod
            def convert(cls, args):
                pass
        
        class MockPlugin2(BaseImportPlugin):
            @classmethod
            def get_name(cls):
                return "mock2"
            
            @classmethod
            def get_description(cls):
                return "Mock plugin 2"
            
            @classmethod
            def create_parser(cls):
                return argparse.ArgumentParser()
            
            @classmethod
            def convert(cls, args):
                pass
        
        # Register the plugins
        PluginRegistry.register(MockPlugin1)
        PluginRegistry.register(MockPlugin2)
        
        # Get all plugins
        plugins = PluginRegistry.get_all_plugins()
        
        # Check that the returned dict is a copy
        assert plugins is not PluginRegistry._plugins
        
        # Check that all plugins are in the dict
        assert "mock1" in plugins
        assert plugins["mock1"] is MockPlugin1
        assert "mock2" in plugins
        assert plugins["mock2"] is MockPlugin2

    def test_discover_plugins(self, monkeypatch):
        """Test discovering plugins in packages."""
        # Create mock packages and modules
        mock_packages = {
            "test_package1": MagicMock(),
            "test_package2": MagicMock(),
            "common": MagicMock()
        }
        
        # Create mock plugin classes
        class MockPlugin1(BaseImportPlugin):
            @classmethod
            def get_name(cls):
                return "mock1"
            
            @classmethod
            def get_description(cls):
                return "Mock plugin 1"
            
            @classmethod
            def create_parser(cls):
                return argparse.ArgumentParser()
            
            @classmethod
            def convert(cls, args):
                pass
        
        class MockPlugin2(BaseImportPlugin):
            @classmethod
            def get_name(cls):
                return "mock2"
            
            @classmethod
            def get_description(cls):
                return "Mock plugin 2"
            
            @classmethod
            def create_parser(cls):
                return argparse.ArgumentParser()
            
            @classmethod
            def convert(cls, args):
                pass
        
        # Add the mock plugins to the mock packages
        mock_packages["test_package1"].MockPlugin1 = MockPlugin1
        mock_packages["test_package2"].MockPlugin2 = MockPlugin2
        
        # Mock pkgutil.iter_modules to return our mock packages
        def mock_iter_modules(paths):
            return [
                (None, "test_package1", True),
                (None, "test_package2", True),
                (None, "common", True),
                (None, "not_a_package", False)
            ]
        
        monkeypatch.setattr("pkgutil.iter_modules", mock_iter_modules)
        
        # Mock importlib.import_module to return our mock packages
        def mock_import_module(name):
            return mock_packages[name]
        
        monkeypatch.setattr("importlib.import_module", mock_import_module)
        
        # Mock inspect.getmembers to return our mock plugins
        def mock_getmembers(obj):
            if obj == mock_packages["test_package1"]:
                return [("MockPlugin1", MockPlugin1)]
            elif obj == mock_packages["test_package2"]:
                return [("MockPlugin2", MockPlugin2)]
            else:
                return []
        
        monkeypatch.setattr("inspect.getmembers", mock_getmembers)
        
        # Mock os.path.dirname to return a fixed path
        monkeypatch.setattr("os.path.dirname", lambda path: "/mock/path")
        monkeypatch.setattr("os.path.abspath", lambda path: path)
        
        # Discover plugins
        PluginRegistry.discover_plugins()
        
        # Check that the plugins were registered
        assert "mock1" in PluginRegistry._plugins
        assert PluginRegistry._plugins["mock1"] is MockPlugin1
        assert "mock2" in PluginRegistry._plugins
        assert PluginRegistry._plugins["mock2"] is MockPlugin2


class TestRegisterPluginDecorator:
    """Tests for the register_plugin decorator."""

    def setup_method(self):
        """Set up the test environment."""
        # Clear the plugin registry before each test
        PluginRegistry._plugins = {}

    def test_register_plugin_decorator(self):
        """Test that the register_plugin decorator registers a plugin."""
        # Create a plugin class with the decorator
        @register_plugin
        class MockPlugin(BaseImportPlugin):
            @classmethod
            def get_name(cls):
                return "mock"
            
            @classmethod
            def get_description(cls):
                return "Mock plugin"
            
            @classmethod
            def create_parser(cls):
                return argparse.ArgumentParser()
            
            @classmethod
            def convert(cls, args):
                pass
        
        # Check that the plugin was registered
        assert "mock" in PluginRegistry._plugins
        assert PluginRegistry._plugins["mock"] is MockPlugin
        
        # Check that the decorator returns the original class
        assert MockPlugin.__name__ == "MockPlugin"