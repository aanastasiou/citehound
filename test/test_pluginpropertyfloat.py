from citehound.plugin import (PluginBase, PluginMetadata, PluginPropertyFloat)
from citehound import CM
import pytest


class ImaginaryPlugin(PluginBase):
    unbounded_optional_float = PluginPropertyFloat()
    positive_optional_float = PluginPropertyFloat()
    negative_optional_float = PluginPropertyFloat()

    
    def __init__(self, citehound_manager=None):
        super().__init__(citehound_manager)
        self._description = PluginMetadata("Imaginary",
                                           "Imagine all the plugins...",
                                           "...launching all at once")

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


