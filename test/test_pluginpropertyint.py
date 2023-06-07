from citehound.plugin import (PluginBase, PluginMetadata, PluginPropertyInt)
from citehound import CM
import pytest

class ImaginaryPlugin(PluginBase):
    unbounded_mandatory_int = PluginPropertyInt()
    positive_optional_int = PluginPropertyInt(default_value=0, vmin=0)
    negative_optional_int = PluginPropertyInt(default_value=-1, vmax=0)

    
    def __init__(self, citehound_manager=None):
        super().__init__(citehound_manager)
        self._description = PluginMetadata("Imaginary",
                                           "Imagine all the plugins...",
                                           "...launching all at once")

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


