"""
Basic definition of the plugin system.

:authors: Athanasios Anastasiou
:date: September 2019
"""

import re

class PluginPropertyBase:
    """
    Models the properties along with their constraints for each plugin
    """
    def __init__(self, default_value=None, prompt="", required=False):
        self._default_value = self.validate(default_value)
        self._prompt = prompt
        self._required = required
        self._private_name = None

    def __set_name__(self, owner, name):
        self._private_name = f"_{name}"

    def __get__(self, obj, obj_type=None):
        if obj is None:
            return self
        else:
            return getattr(obj, self._private_name)

    def __set__(self, object, value):
        setattr(object, self._private_name, self.validate(value))

    def validate(self, a_value):
        return a_value

    @property
    def prompt(self):
        return self.prompt

    @property
    def default_value(self):
        return self._default_value


class PluginPropertyInt(PluginPropertyBase):
    def __init__(self, default_value=0, prompt="", vmin=None, vmax=None):
        super().__init__(default_value, prompt)
        self._vmin = vmin
        self._vmax = vmax
    
    @property
    def vmin(self):
        return self._vmin

    @property
    def vmax(self):
        return self._vmax

    def validate(self, new_value):
        if not issubclass(type(new_value), int):
            raise TypeError(f"{self._name} expects int or float, received {type(new_value)}")
        if self._vmin is not None:
            if new_value < self._vmin:
                raise ValueError(f"Expected value to be {self._vmin} > x, received {new_value}")
        if self._vmax is not None:
            if new_value > self._vmax:
                raise ValueError(f"Expected value to be x < {self._vmax}, received {new_value}")
        return int(new_value)


class PluginPropertyFloat(PluginPropertyBase):
    def __init__(self, default_value=0.0, prompt="", vmin=None, vmax=None):
        super().__init__(default_value, prompt)
        self._vmin = vmin
        self._vmax = vmax
    
    @property
    def vmin(self):
        return self._vmin

    @property
    def vmax(self):
        return self._vmax

    def validate(self, new_value):
        if not issubclass(type(new_value), float):
            raise TypeError(f"{self._name} expects int or float, received {type(new_value)}")
        if self._vmin is not None:
            if new_value < self._vmin:
                raise ValueError(f"Expected value to be {self._vmin} > x, received {new_value}")
        if self._vmax is not None:
            if new_value > self._vmax:
                raise ValueError(f"Expected value to be x < {self._vmax}, received {new_value}")
        return float(new_value)


class PluginPropertyString(PluginPropertyBase):
    def __init__(self, default_value=0.0, prompt="", choices=None, max_length=None):
        super().__init__(default_value, prompt)
        self._choices = choices
        self._max_length = max_length

    @property
    def choices(self):
        return self._choices.keys()

    @property
    def max_length(self):
        return self._max_length

    def validate(self, new_value):
        if not issubclass(type(new_value), str):
            raise TypeError(f"{self._name} expects str, received {type(new_value)}")
        if self._max_length is not None:
            if len(new_value) >= max_length:
                raise ValueError(f"{self._name} should be at most {self._max_length} characters long, was {len(new_value)}")
        if self._choices is not None:
            if new_value not in self_choices:
                raise ValueError(f"{self._name} expects values in {list(self._choices.keys())}, received {new_value}")
            return self._choices[new_value]
        return new_value


class PluginPropertyRegexProperty(PluginPropertyBase):
    def __init__(self, default_value=None, prompt="", expression=None):
        super().__init__(default_value, prompt)
        self._expression = re.compile(expression)

    @property
    def expression(self):
        return self._expression

    def validate(self, new_value):
        if not issubclass(type(new_value), str):
            raise TypeError(f"{self._name} expects str, received {type(new_value)}")
        if not self._expression.match(new_value):
            raise ValueError(f"{self._name} is expected to conform to {self._expression}, received {new_value}")
        return new_value


class PluginPropertyBoolean(PluginPropertyBase):
    def validate(self, new_value):
        if not issubclass(type(new_value), bool):
            raise TypeError(f"{self._name} expects bool, received {type(new_value)}")
        return new_value


class PluginBase:
    """
    Abstract class for plugins.
    
    All parameters that the plugin exposes to its environment, need to be set as properties.
    """
    def __init__(self):
        self._is_active = False
        self._description = {}
        self.reset()

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

    def reset(self):
        for a_var in vars(self.__class__):
            if issubclass(type(getattr(self.__class__,a_var)), PPropertyDescriptorBase):
                setattr(self, a_var, getattr(self.__class__,a_var).default_value)


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
