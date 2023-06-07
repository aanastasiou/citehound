from . import PluginPropertyBase, SpecialPropertyValues
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
        """
        Fires up the parameter UI and sets up a plugin object.

        :returns: None if setting the plugin up proceeded with no errors, otherwise a list of error messages
        """
        
        plugin_type = type(self._plugin_object)

        plugin_param_errors = []

        for a_var in vars(plugin_type):
            if issubclass(type(getattr(plugin_type, a_var)), PluginPropertyBase) and getattr(self._plugin_object, a_var) is SpecialPropertyValues.UNDEFINED:
                valid_value_entered = False
                while not valid_value_entered:
                    user_value = prompt_toolkit.prompt(getattr(getattr(plugin_type, a_var),"prompt"))
                    try:
                        setattr(self._plugin_object, a_var, user_value)
                        valid_value_entered = True
                    except (ValueError, TypeError) as e:
                        prompt_toolkit.print_formatted_text("{e}. Please try again")

