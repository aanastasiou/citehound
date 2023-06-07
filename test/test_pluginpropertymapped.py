from citehound.plugin import (PluginBase, PluginMetadata, PluginPropertyMapped)
from citehound import CM
import pytest

class ImaginaryPlugin(PluginBase):
    optional_mapped = PluginPropertyMapped(default_value="yes", valid_values={"yes":True, "no":False})


def test_mapped_property():
    """
    Mapped properties should only allow the values in their mappings.
    """

    u = ImaginaryPlugin()

    # This should not raise an exception
    u.optional_mapped = "no"
    with pytest.raises(ValueError):
        u.optional_mapped = "maybe"


 
