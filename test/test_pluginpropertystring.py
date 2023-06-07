from citehound.plugin import (PluginBase, PluginMetadata, PluginPropertyString)
from citehound import CM
import pytest

class ImaginaryPlugin(PluginBase):
    optional_len_bounded_string = PluginPropertyString(default_value="Some Value", max_length=20)
    optional_choice_bounded_string = PluginPropertyString(default_value="Beta", choices={"Alpha":"ALPHA", "Beta":"BETA"})

def test_propertystring_bounded_length():
    """
    String properties should allow strings of specified length
    """
    u = ImaginaryPlugin()
    u.optional_len_bounded_string = "Green and submarine"

    with pytest.raises(ValueError):
        u.optional_len_bounded_string = "This string should be longer than 20 characters to fail the max_length constraint"

def test_propertystring_bounded_choice():
    """
    String properties should allow only string values within their "choices" constraints
    """
    u = ImaginaryPlugin()

    with pytest.raises(ValueError):
        u.optional_choice_bounded_string = "Cyan"

    # These should proceed without raising any exception
    u.optional_choice_bounded_string = "Alpha"

    # Choice strings are initialised via a mapping, here "Black":"White"
    assert u.optional_choice_bounded_string == "ALPHA"




