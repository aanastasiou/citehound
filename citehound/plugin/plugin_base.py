"""
Basic definition of the plugin system.

:authors: Athanasios Anastasiou
:date: September 2019
"""

import re

class PluginPropertyBase:
    """
    Models the properties along with their constraints for each plugin parameter
    """
    def __init__(self, default_value=None, prompt="", required=False):
        self._default_value = default_value 
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
    """
    Enforces properties to validate an integer number.

    An integer number (x) can have:

    * A `default_value`
    * A `prompt` (that provides a hint to user interfaces used to populate a given variable).
    * `vmin, vmax` such that `vmin < x < vmax`. 
    """
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
        self.on_before_process()
        self.on_process()
        self.on_after_process()

    def __repr__(self):
        return f"             Name:{self.description['name']}\nShort Description:{self.description['short_desc']}\n Long Description:{self.description['long_desc']}\n"

    def reset(self):
        for a_var in vars(self.__class__):
            if issubclass(type(getattr(self.__class__,a_var)), PluginPropertyBase):
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
#     @property
#     def plugin(self):
#         return self._plugin_object
# 
#     def on_setup_plugin(self):
#         """Fires up the parameter UI and sets up a plugin object."""
 
