"""
Basic definition of the plugin system.

:authors: Athanasios Anastasiou
:date: September 2019
"""

class PluginPropertyBase:
    """
    Models the properties along with their constraints for each plugin
    """
    def __init__(self, default_value, prompt=""):
        self._value = None
        self._default_value = self.validate(default_value)
        self._prompt = prompt

    def validate(self, a_value):
        return a_value

    @property
    def prompt(self):
        return self.prompt

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = self.validate(new_value)

    def reset(self):
        self._value = self._default_value


class PluginPropertyInt(PluginPropertyBase):
    def __init__(self, default_value=0):
        super().__init__(default_value)

    def validate(self, a_value):
        return int(a_value)


class PluginPropertyFloat(PluginPropertyBase):
    def __init__(self, default_value=0.0):
        super().__init__(default_value)

    def validate(self, a_value):
        return float(a_value)


class PluginPropertyString(PluginPropertyBase):
    def __init__(self, default_value="", str_pattern=None):
        self._str_pattern = str_pattern
        super().__init__(default_value)

    def validate(self, a_value):
        if str_pattern is None:
            return str(a_value)
        else:
            try:
                if not self._str_pattern.match(a_value):
                    raise Exception(f"{a_value} does not conform to the string pattern")
                else:
                    return str(a_value)
            except TypeError:
                raise Exception(f"Expected string received {a_value}")


class PluginBase:
    """
    Abstract class for plugins.
    
    All parameters that the plugin exposes to its environment, need to be set as properties.
    """
    def __init__(self):
        self._is_active = False
        self._description = {}

    @property
    def description(self):
        """Returns a dictionary with human readable descriptions of the plugin's functionality.
        
        The dictionary has the following structure:

        name:str
        short_desc: str
        long_desc: str

        """
        return self._description

    @property
    def active(self):
        return self._is_active

    @active.setter
    def active(self, new_state):
        self._is_active = new_state

    def on_init_plugin(self):
        """Initialise the plugin and make sure that its state is valid."""
        pass

    def on_cleanup_plugin(self):
        """Called on taking down the plugin"""
        pass

    def on_reset_plugin(self):
        """Called to reset the state of the plugin without re-initialising it"""
        pass

    def on_before_process(self):
        """Called just before the main processing step."""
        return frame_in

    def on_process(self):
        """Performs the main processing step."""
        return frame_in

    def on_after_process(self):
        """Called just after the main processing step."""
        return frame_in

    def __call__(self):
        if not self._is_active:
            return frame_in
        
        self.on_before_process()
        self.on_process()
        self.on_after_process()

    def __repr__(self):
        return f"             Name:{self.description['name']}\nShort Description:{self.description['short_desc']}\n Long Description:{self.description['long_desc']}\n"


# class PluginAdapter:
#     """
#     A plugin adapter wraps a seqbrowser plugin in a set of calls that add GUI capabilities to it.
# 
#     The adapter is completely agnostic of the internals of the plugin.
#     """
#     def __init__(self, path_to_plugin, main_app_win):
#         super().__init__()
#         # TODO: Med, Default values are already assigned to properties on initialisation. Need to take them into account
#         #       during type inference rather than relying on decoding the docstring which was a quick solution here.
#         self._type_rule = re.compile(":type (?P<variable_name>[a-zA-Z_][a-zA-Z_0-9]*):\s*(?P<variable_type>int|float|str|tuple)")
#         # TODO: Med, this needs to throw exception if anything goes wrong with loading the plugin.
#         plugin_module = importlib.import_module(path_to_plugin)
#         # TODO: Med, This needs to throw an exception if it does not find the variable or the returned class is not
#         #       of the right type
#         plugin_class = plugin_module.PUBLISHED_PLUGIN
#         self._plugin_params = {}
#         # Create the hosted plugin object
#         self._plugin_object = plugin_class()
#         # Recover params
#         plugin_name = path_to_plugin.split(".")[-1]
#         for a_plugin_param in vars(plugin_class).items():
#             if isinstance(a_plugin_param[1], property):
#                 infer_type = self._type_rule.search(plugin_class.__dict__[a_plugin_param[0]].__doc__)
#                 # TODO: HIGH, Throw exceptions if the type has been omitted or does not match.
#                 self._plugin_params[a_plugin_param[0]] = infer_type.groupdict()
#         # Create the UI object to edit the parameters
#         ui_class_name = f"{plugin_name}_ModifyParamUI"
#         ui_params = {}
#         for a_plugin_param in self._plugin_params.items():
#             v_dtype = a_plugin_param[1]["variable_type"]
#             if v_dtype == "int":
#                 ui_params[a_plugin_param[0]] = gd_dataitems.IntItem(f'{a_plugin_param[0]}')
#             if v_dtype == "tuple":
#                 ui_params[a_plugin_param[0]] = gd_dataitems.StringItem(f'{a_plugin_param[0]}')
#             if v_dtype == "float":
#                 ui_params[a_plugin_param[0]] = gd_dataitems.FloatItem(f'{a_plugin_param[0]}')
#             if v_dtype == "str":
#                 ui_params[a_plugin_param[0]] = gd_dataitems.StringItem(f'{a_plugin_param[0]}')
#         self._ui_modify_plugin_params_object = type(ui_class_name, (gd_datatypes.DataSet,), ui_params)()
#         # Create the UI object that can stay open while the browser is running to be able to inspect its output.
#         self._ui_show_plugin_params_object = DataSetShowDialog(instance=self._ui_modify_plugin_params_object,
#                                                                parent=main_app_win)
#         self._ui_show_plugin_params_object.setModal(False)
# 
#     @property
#     def plugin(self):
#         return self._plugin_object
# 
#     def on_setup_plugin(self):
#         """Fires up the parameter UI and sets up a plugin object."""
#         ui_ok = self._ui_modify_plugin_params_object.edit()
#         if ui_ok:
#             for a_plugin_param in self._plugin_params.items():
#                 v_dtype = a_plugin_param[1]
#                 # TODO: MED, Get rid of this eval or split it into two controls to perform more validation on it.
#                 if v_dtype["variable_type"] == "tuple":
#                     setattr(self._plugin_object, a_plugin_param[0],
#                             eval(getattr(self._ui_modify_plugin_params_object, a_plugin_param[0])))
#                 else:
#                     setattr(self._plugin_object, a_plugin_param[0], getattr(self._ui_modify_plugin_params_object,
#                                                                             a_plugin_param[0]))
# 
