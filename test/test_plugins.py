"""
Complete tests for the plugin system


:author: Athanasios Anastasiou
:date: May 2023
"""

from citehound.plugin import (PluginBase, PluginPropertyInt, PluginPropertyFloat, 
                       PluginPropertyString, PluginPropertyRegex, PluginPropertyMapped)

import pytest


class ImaginaryPlugin(PluginBase):
    unbounded_optional_int = PluginPropertyInt(default_value = 0,
                                               prompt="Enter an integer",
                                               help_str="An integer property"
                                              )
    
    unbounded_mandatory_int = PluginPropertyInt(prompt="Enter an integer",
                                                help_str="An integer property"
                                               )

    positive_optional_int = PluginPropertyInt(default_value=1,
                                              vmin=0)
    negative_optional_int = PluginPropertyInt(default_value=-1,
                                              vmax=0)
    
    unbounded_optional_float = PluginPropertyInt(default_value=3.1415928)

    positive_optional_float = PluginPropertyInt(default_value=3.1415928, 
                                       vmin=0.0)

    negative_optional_float = PluginPropertyInt(default_value=-3.1415928,
                                       vmax=0.0)
    
    optional_unbounded_string = PluginPropertyString(default_value="Nikos Kazantzakis")
    optional_bounded_string = PluginPropertyString(default_value="Nikos Kazantzakis", max_length=20)
    optional_bounded_quant_string = PluginPropertyString(default_value="White", choices={"White":"Black", "Black":"White"})

    optional_regex = PluginPropertyRegex(default_value="SOME_VAR", expression="[A-Z_][A-Z_]*")

    optional_mapped = PluginPropertyMapped(default_value="no")

    def __init__(self):
        super().__init__()
        self._description = {"name":"Imaginary",
                             "short_desc":"Imagine all the plugins...",
                             "long_desc":"...launching all at once"}


def test_init_metadata():
    """
    Each property carries metadata
    """
    u = ImaginaryPlugin()

    user_properties = u.user_properties

    assert user_properties["unbounded_optional_int"]["prompt"] == "Enter an integer"
    assert user_properties["unbounded_optional_int"]["help_str"] == "An integer property"
    assert user_properties["unbounded_optional_int"]["default_value"] == 0
    assert u.unbounded_mandatory_int is None

def test_pluginbase_metadata():
    """
    Every plugin carries metadata
    """

    u = ImaginaryPlugin()

    assert u.description["name"] == "Imaginary"
    assert u.description["short_desc"] == "Imagine all the plugins..."
    assert u.description["long_desc"] == "...launching all at once"

def test_pluginbase_userproperties():
    """
    Every plugin returns the right number and metadata for its user properties.
    """
    u = ImaginaryPlugin()

    assert len(u.user_properties) == 12
    assert type(u.user_properties) is dict
    assert len(u.user_properties["unbounded_optional_int"]) == 3

def test_rest_pluginbase():
    """
    Every plugin includes reset functionality to bring it back to its default
    state just after initialisation.
    """
    u = ImaginaryPlugin()

    # There is only one mandatory property in the imaginary plugin
    # which will cause a Typeerror exception

    with pytest.raises(TypeError):
        u()

    # Once this mandatory variable has received a valid value...
    u.unbounded_mandatory_int = 42

    # ...execution should proceed normally...
    assert u() is None

    # ...and once the plugin is reset...
    u.reset()

    # ...it should py failing again if the mandatory variables have not been set.
    with pytest.raises(TypeError):
        u()

def test_uninitialised_mandatory_props():
    u = ImaginaryPlugin()

    # There is only one mandatory property in the imaginary plugin
    # which will cause a Typeerror exception

    with pytest.raises(TypeError):
        u()

    # Once this mandatory variable has received a valid value...
    u.unbounded_mandatory_int = 42

    # Execution should proceed normally.
    assert u() is None


def test_propertyint_validation():
    """
    Integer plugin properties should only allow integer values and exclude others
    """

    u = ImaginaryPlugin()

    with pytest.raises(ValueError):
        u.unbounded_mandatory_int = "Alpha"

    with pytest.raises(TypeError):
        u.unbounded_mandatory_int = None

    # This should still work because "120" can be converted to an int
    u.unbounded_mandatory_int = "120"


def test_propertyint_bounds():
    """
    Integer plugin properties should only allow integer values within a particular range
    """

    u = ImaginaryPlugin()

    u.unbounded_mandatory_int = 120

    with pytest.raises(ValueError):
        u.positive_optional_int = -120

    with pytest.raises(ValueError):
        u.negative_optional_int = 120

    # The following two should not raise exceptions
    u.positive_optional_int = 120
    u.negative_optional_int = -120


def test_propertyfloat_bounds():
    """
    Floating point properties should only allow floating point numbers within specified bounds.
    """
    u = ImaginaryPlugin()
 
    with pytest.raises(ValueError):
        u.positive_optional_float = -1.2

    with pytest.raises(ValueError):
        u.negative_optional_float = 2.1

    # The following two should not raise exceptions
    u.positive_optional_int = 3.1415928
    u.negative_optional_int = -1
    u.unbounded_optional_float = 2.1


def test_propertystring_bounds():
    """
    String properties should allow strings of specified length or within a specific set of values.
    """

    u = ImaginaryPlugin()

    # This should not raise an exception
    u.optional_unbounded_string = "Something something something something something dark side"

    with pytest.raises(ValueError):
        u.optional_bounded_string = "This string should be longer than 20 characters to fail the max_len specification"

    with pytest.raises(ValueError):
        u.optional_bounded_quant_string = "Cyan"

    # These should proceed without raising any exception
    u.optional_bounded_string = "A short string"
    u.optional_bounded_quant_string = "Black"
    # Choice strings are initialised via a mapping, here "Black":"White"
    assert u.optional_bounded_quant_string == "White"

    
def test_propertyregex():
    """
    Regex properties should only allow strings that conform to their rule
    """

    u = ImaginaryPlugin()

    # This should not raise an exception
    u.optional_regex = "ANOTHER_VAR"

    with pytest.raises(ValueError):
        u.optional_regex = "mary had a little lamb"


def test_propertymapped():
    """
    Mapped properties should only accept values in their set of allowable values
    """

    u = ImaginaryPlugin()

    # This should not raise an exception
    u.optional_mapped = "yes"
    u.optional_mapped = "no"

    with pytest.raises(ValueError):
        u.optional_mapped = "maybe"



