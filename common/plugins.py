"""
Plugin architecture for import sources.

This module provides a base class and plugin discovery mechanism for import sources.
Each import source (like Evernote, Pocket, etc.) should implement a plugin that inherits
from the BaseImportPlugin class and registers itself with the plugin registry.
"""

import abc
import argparse
import importlib
import inspect
import os
import pkgutil
import sys
from typing import Dict, List, Optional, Type

from common.cli import create_base_parser


class BaseImportPlugin(abc.ABC):
    """
    Base class for import source plugins.
    
    All import source plugins should inherit from this class and implement
    the required methods.
    """
    
    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """
        Get the name of the import source.
        
        Returns
        -------
        str
            The name of the import source (e.g., 'evernote', 'pocket').
        """
        pass
    
    @classmethod
    @abc.abstractmethod
    def get_description(cls) -> str:
        """
        Get a description of the import source.
        
        Returns
        -------
        str
            A description of the import source.
        """
        pass
    
    @classmethod
    @abc.abstractmethod
    def create_parser(cls) -> argparse.ArgumentParser:
        """
        Create an argument parser for this import source.
        
        Returns
        -------
        argparse.ArgumentParser
            An argument parser configured for this import source.
        """
        pass
    
    @classmethod
    @abc.abstractmethod
    def convert(cls, args: argparse.Namespace) -> None:
        """
        Convert the input file to CSV format.
        
        Parameters
        ----------
        args : argparse.Namespace
            Parsed command line arguments.
        
        Returns
        -------
        None
            The function processes files and doesn't return a value.
        """
        pass


class PluginRegistry:
    """
    Registry for import source plugins.
    
    This class maintains a registry of all available import source plugins
    and provides methods to discover and access them.
    """
    
    _plugins: Dict[str, Type[BaseImportPlugin]] = {}
    
    @classmethod
    def register(cls, plugin_class: Type[BaseImportPlugin]) -> None:
        """
        Register a plugin with the registry.
        
        Parameters
        ----------
        plugin_class : Type[BaseImportPlugin]
            The plugin class to register.
        """
        plugin_name = plugin_class.get_name()
        cls._plugins[plugin_name] = plugin_class
    
    @classmethod
    def get_plugin(cls, name: str) -> Optional[Type[BaseImportPlugin]]:
        """
        Get a plugin by name.
        
        Parameters
        ----------
        name : str
            The name of the plugin to get.
        
        Returns
        -------
        Optional[Type[BaseImportPlugin]]
            The plugin class if found, None otherwise.
        """
        return cls._plugins.get(name)
    
    @classmethod
    def get_all_plugins(cls) -> Dict[str, Type[BaseImportPlugin]]:
        """
        Get all registered plugins.
        
        Returns
        -------
        Dict[str, Type[BaseImportPlugin]]
            A dictionary mapping plugin names to plugin classes.
        """
        return cls._plugins.copy()
    
    @classmethod
    def discover_plugins(cls) -> None:
        """
        Discover and register all available plugins.
        
        This method searches for plugins in all packages in the project
        and registers them with the registry.
        """
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Discover all packages in the project
        for _, package_name, is_pkg in pkgutil.iter_modules([project_root]):
            if is_pkg and package_name != 'common':
                # Import the package
                package = importlib.import_module(package_name)
                
                # Search for plugin classes in the package
                for _, obj in inspect.getmembers(package):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseImportPlugin) and 
                        obj is not BaseImportPlugin):
                        # Register the plugin
                        cls.register(obj)


def register_plugin(plugin_class: Type[BaseImportPlugin]) -> Type[BaseImportPlugin]:
    """
    Decorator to register a plugin with the registry.
    
    Parameters
    ----------
    plugin_class : Type[BaseImportPlugin]
        The plugin class to register.
    
    Returns
    -------
    Type[BaseImportPlugin]
        The plugin class (unchanged).
    """
    PluginRegistry.register(plugin_class)
    return plugin_class