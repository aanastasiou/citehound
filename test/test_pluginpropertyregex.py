from citehound.plugin import (PluginBase, PluginMetadata, PluginPropertyRegex)
from citehound import CM
import pytest

class ImaginaryPlugin(PluginBase):
    optional_regex_property = PluginPropertyRegex("[a-z_][a-z]+")


def test_propertyregex():
    """
    Regex properties should only allow strings that conform to their rule
    """

    u = ImaginaryPlugin()

    # This should not raise an exception
    u.optional_regex_property = "_a"

    with pytest.raises(ValueError):
        u.optional_regex_property = "MARY HAD A LITTLE LAMB"


