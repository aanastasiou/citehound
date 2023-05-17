import pkgutil
import importlib
import re

class PluginManager:
    """
    Lists and launches Citehound plugins

    Plugins:

    * Are normal python modules with their own dependencies / documentation
    * All share the prefix ``citehound-plugin-`` (otherwise, even if installed they cannot be discovered)
    """

    def __init__(self):
        pass

    def list_plugins(self):
        # Scan installed plugins
        installed_plugins = list(map(lambda x:x.name, 
                                     filter(lambda x:"citehound_plugin_" in x.name, 
                                            pkgutil.iter_modules())))
        final_list = []
        for a_plugin in installed_plugins:
            if "__editable__" in a_plugin:
                module_to_append = list(importlib.import_module(a_plugin).MAPPING.keys())[0] # Only one module is expected in each plugin.
            else:
                module_to_append = a_plugin

            final_list.append(module_to_append.replace("citehound_plugin_", ""))

        return final_list

    def launch_plugin(self):
        pass


