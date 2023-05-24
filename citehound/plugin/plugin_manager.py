import pkgutil
import importlib
import re
from .. import exceptions

class PluginManager:
    """
    Lists and launches Citehound plugins

    Plugins:

    * Are normal python modules with their own dependencies / documentation
    * All share the prefix ``citehound-plugin-`` (otherwise, even if installed they cannot be discovered)
    """

    def __init__(self):
        # Scan installed plugins
        installed_plugins = list(map(lambda x:x.name, 
                                     filter(lambda x:"citehound_plugin_" in x.name, 
                                            pkgutil.iter_modules())))
        final_list = []
        for a_plugin in installed_plugins:
            # Editable plugins are handled slightly differently, because they
            # return a "finder" rather than the module itself
            if "__editable__" in a_plugin:
                module_to_append = list(importlib.import_module(a_plugin).MAPPING.keys())[0] # Only one module is expected in each plugin.
            else:
                module_to_append = a_plugin

            final_list.append(module_to_append.replace("citehound_plugin_", ""))
        self._installed_plugins = final_list

    @property
    def installed_plugins(self):
        """
        Returns a list of the installed citehound plugins
        """
        return self._installed_plugins

    def load_plugin(self, a_plugin):
        """
        Loads a plugin by name
        """
        # TODO: HIGH, must add more sanitation to a_plugin
        try:
            return importlib.import_module(f"citehound_plugin_{a_plugin}").EXPORTED_PLUGIN
        except ModuleNotFoundError:
            raise exceptions.PluginNotFound(f"Plugin citehound_plugin_{a_plugin} is not installed.")


