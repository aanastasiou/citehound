"""
Basic definition of the plugin system.

:authors: Athanasios Anastasiou
:date: September 2019
"""

import re
import os
import pathlib
import collections

PluginMetadata = collections.namedtuple("PluginMetadata",
                                        ["name", "short_desc", "long_desc"],
                                        defaults = [None, None])

class PluginPropertyBase:
    """
    Models the properties along with their constraints for each user-facing plugin parameter.

    This is a Python descriptor.

    :param default_value:
    :param prompt:
    :param help_str:

    :type default_value:
    :type prompt:
    :type help_str:

    """
    # TODO: HIGH, enable the mandatory / optional value passing
    def __init__(self, default_value=None, prompt="", help_str=""):
        self._default_value = default_value if default_value is None else self.validate(default_value)
        self._prompt = prompt
        self._private_name = None
        self._help_str = help_str

    def __set_name__(self, owner, name):
        """
        Creates the private member attribute.
        """
        self._private_name = f"_{name}"
        setattr(owner, self._private_name, self._default_value)

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
        return self._prompt

    @property
    def default_value(self):
        return self._default_value

    @property
    def help_str(self):
        return self._help_str


class PluginPropertyInt(PluginPropertyBase):
    """
    Enforces properties to validate an integer number.

    An integer number (x) can have:

    * A `default_value`
    * A `prompt` (that provides a hint to user interfaces used to populate a given variable).
    * `vmin, vmax` such that `vmin < x < vmax`. 
    """
    def __init__(self, default_value=None, prompt="", help_str="", vmin=None, vmax=None):
        self._vmin = vmin
        self._vmax = vmax
        super().__init__(default_value, prompt, help_str)
    
    @property
    def vmin(self):
        return self._vmin

    @property
    def vmax(self):
        return self._vmax

    def validate(self, new_value):
        try:
            new_value = int(new_value)
        except ValueError:
            raise ValueError(f"Expected a valid integer value, received {new_value}")

        if self._vmin is not None:
            if new_value < self._vmin:
                raise ValueError(f"Expected value to be x > {self._vmin}, received {new_value}")
        if self._vmax is not None:
            if new_value > self._vmax:
                raise ValueError(f"Expected value to be x < {self._vmax}, received {new_value}")
        return int(new_value)


class PluginPropertyFloat(PluginPropertyBase):
    def __init__(self, default_value=None, prompt="", help_str="", vmin=None, vmax=None):
        self._vmin = vmin
        self._vmax = vmax
        super().__init__(default_value, prompt, help_str)
    
    @property
    def vmin(self):
        return self._vmin

    @property
    def vmax(self):
        return self._vmax

    def validate(self, new_value):

        try:
            new_value = float(new_value)
        except ValueError:
            raise ValueError(f"Expected a valid Real value, received {new_value}")

        if self._vmin is not None:
            if new_value < self._vmin:
                raise ValueError(f"Expected value to be {self._vmin} > x, received {new_value}")

        if self._vmax is not None:
            if new_value > self._vmax:
                raise ValueError(f"Expected value to be x < {self._vmax}, received {new_value}")

        return float(new_value)


class PluginPropertyString(PluginPropertyBase):
    def __init__(self, default_value=None, prompt="", help_str="", choices=None, max_length=None):
        self._choices = choices
        self._max_length = max_length
        super().__init__(default_value, prompt, help_str)

    @property
    def choices(self):
        return self._choices.keys()

    @property
    def max_length(self):
        return self._max_length

    def validate(self, new_value):
        if not issubclass(type(new_value), str):
            raise TypeError(f"{self._private_name} expects str, received {type(new_value)}")
        if self._max_length is not None:
            if len(new_value) >= self._max_length:
                raise ValueError(f"{self._private_name} should be at most {self._max_length} characters long, was {len(new_value)}")
        if self._choices is not None:
            if new_value not in self._choices:
                raise ValueError(f"{self._private_name} expects values in {list(self._choices.keys())}, received {new_value}")
            return self._choices[new_value]
        return new_value


class PluginPropertyRegex(PluginPropertyBase):
    def __init__(self, expression, default_value=None, prompt="", help_str="") :
        self._expression = re.compile(expression)
        super().__init__(default_value, prompt, help_str)

    @property
    def expression(self):
        return self._expression

    def validate(self, new_value):
        if not issubclass(type(new_value), str):
            raise TypeError(f"{self._private_name} expects str, received {type(new_value)}")
        if not self._expression.match(new_value):
            raise ValueError(f"{self._private_name} is expected to conform to {self._expression}, received {new_value}")
        return new_value


class PluginPropertyMapped(PluginPropertyBase):
    def __init__(self, default_value=None, prompt="", help_str="", valid_values={"yes":True, "no":False}):
        self._valid_values = valid_values
        super().__init__(default_value, prompt, help_str)

    @property
    def valid_values(self):
        return self._valid_values
    
    def validate(self, new_value):
        if new_value not in self._valid_values.keys():
            raise ValueError(f"Value expected in {list(self._valid_values.keys())}, received {new_value}")

        if not issubclass(type(new_value), str):
            raise TypeError(f"{self._private_name} expects str, received {type(new_value)}")

        return self._valid_values[new_value]


class PluginPropertyFSPath(PluginPropertyBase):
    """
    Manages a path property

    :param file_okay: Whether the path should point to a file.
    :type file_okay: bool
    :param dir_okay: Whether the path should point to a directory.
    :type dir_okay: bool
    :param resolve_path: Whether the path should be resolved (i.e. even 
                         relative paths being stored in the property as absolute)
    :type resolve_path: bool
    :param writeable: Whether the path should be writeable by the current process.
    :type writeable: bool
    :param readable: Whether the path should be readable by the current process.
    :type readable: bool
    :param executable: Whether the path should be executable by the current process.
    :type executable: bool
    :param exists: Whether the path should exist or not (at the time of validation).
    :type exists: bool
    """
    def __init__(self, default_value=None, prompt="", help_str="", 
                 file_okay = True, dir_okay=True, resolve_path=False, 
                 writeable=False, readable=True, executable=False,
                 exists=False):
        self._file_okay = file_okay
        self._dir_okay = dir_okay
        self._resolve_path = resolve_path
        self._writeable = writeable
        self._readable = readable
        self._executable = executable
        self._exists = exists

        super().__init__(default_value, prompt, help_str)

    @property
    def file_okay(self):
        return self._file_okay

    @property
    def dir_okay(self):
        return self._dir_okay

    @property
    def resolve_path(self):
        return self._resolve_path

    @property
    def writeable(self):
        return self._writeable

    @property
    def readable(self):
        return self._readable
    
    @property
    def executable(self):
        return self._executable

    @property
    def exists(self):
        return self._exists

    def validate(self, new_value):
        if not issubclass(type(new_value), str):
            raise TypeError(f"{self._private_name} expects str, received {type(new_value)}")

        new_path = pathlib.Path(new_value)

        if self._resolve_path:
            new_path = new_path.resolve()

        if self._exists:
            if not new_path.exists():
                raise ValueError(f"{self._private_name} expects an existing file, received {new_path} which does not exist")

            if self._dir_okay and not new_path.is_dir():
                raise ValueError(f"{self._private_name} expects directory, received {new_path}")

        if self._file_okay and not new_path.is_file():
            raise ValueError(f"{self._private_name} expects a file, received {new_path}")

        if self._executable and not os.access(new_path, os.X_OK):
            raise ValueError(f"{self._private_name} expects an executable path and {new_path} is not")

        if self._writeable and not os.access(new_path, os.W_OK):
            raise ValueError(f"{self._private_name} expects a writeable path and {new_path} is not")

        if self._readable and not os.access(new_path, os.R_OK):
            raise ValueError(f"{self._private_name} expects a readable path and {new_path} is not")


class PluginBase:
    """
    Abstract class for plugins.
    
    All parameters that the plugin exposes to its environment, need to be set as properties.
    """
    def __init__(self, citehound_manager=None):
        self._description = PluginMetadata(name = "PluginBase")
        self._cm_object = citehound_manager
        self.reset()

    @property
    def current_cm(self):
        """
        Returns the CitehoundManager object that was passed to the plugin during initialisation.

        All operations towards the current database should be applied directly via this object.
        """
        return self._cm_object

    @property
    def description(self):
        """Returns a PluginMetadata named tuple with human readable descriptions of the plugin's functionality.
        
        The named tuple has the following structure:

        name:str
        short_desc: str
        long_desc: str

        """
        return self._description

    @property
    def user_properties(self):
        """
        Return metadata associated with the parameters of a plugin.
        """
        var_metadata={}
        for a_var in vars(self.__class__):
            if issubclass(type(getattr(self.__class__, a_var)), PluginPropertyBase):
                var_metadata[a_var] = {"default_value": getattr(self.__class__, a_var).default_value,
                                       "prompt": getattr(self.__class__, a_var).prompt,
                                       "help_str": getattr(self.__class__, a_var).help_str,
                                       }
        return var_metadata

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
        pass

    def on_process(self):
        """Performs the main processing step."""
        pass

    def on_after_process(self):
        """Called just after the main processing step."""
        pass

    def __call__(self):
        # Check that a valid Citehound Manager has been passed as a parameter
        # TODO: HIGH, Add a proper exception from the CM hierarchy below
        if self._cm_object is None:
            raise Exception("Plugins expect a valid CM")

        # Check that all mandatory parameters have been given appropriate values
        for prop, prop_metadata in self.user_properties.items():
            if prop_metadata["default_value"] is None and \
               getattr(self, f"_{prop}") is None:
                   raise ValueError(f"Parameter {prop} is mandatory but has not been set.")

        self.on_before_process()
        self.on_process()
        self.on_after_process()

    def __repr__(self):
        return f"             Name:{self.description.name}\nShort Description:{self.description.short_desc}\n Long Description:{self.description.long_desc}\n"

    def reset(self):
        for a_var in vars(self.__class__):
            if issubclass(type(getattr(self.__class__,a_var)), PluginPropertyBase):
                setattr(self, f"_{a_var}", getattr(self.__class__,a_var).default_value)
        self.on_reset_plugin()

    
