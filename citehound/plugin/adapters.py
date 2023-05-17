from . import PluginPropertyBase
import prompt_toolkit

class PluginAdapterTUI:
    """
    Wraps a plugin in a set of calls that enable a Text GUI to populate its user facing attributes.

    The adapter is completely agnostic of the internals of the plugin.
    """
    def __init__(self, plugin_object):
        self._plugin_object = plugin_object

    @property
    def plugin(self):
        return self._plugin_object

    def setup_plugin(self):
        """Fires up the parameter UI and sets up a plugin object."""
        plugin_type = type(self._plugin_object)
        for a_var in vars(plugin_type):
            if issubclass(type(getattr(plugin_type, a_var)), PluginPropertyBase):
                user_value = prompt_toolkit.prompt(getattr(getattr(plugin_type, a_var),"prompt"))
                setattr(self._plugin_object, a_var, user_value)





# # TODO: Med, Default values are already assigned to properties on initialisation. Need to take them into account
# #       during type inference rather than relying on decoding the docstring which was a quick solution here.
# self._type_rule = re.compile(":type (?P<variable_name>[a-zA-Z_][a-zA-Z_0-9]*):\s*(?P<variable_type>int|float|str|tuple)")
# # TODO: Med, this needs to throw exception if anything goes wrong with loading the plugin.
# plugin_module = importlib.import_module(path_to_plugin)
# # TODO: Med, This needs to throw an exception if it does not find the variable or the returned class is not
# #       of the right type


