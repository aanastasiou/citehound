from citehound.plugin import (PluginBase, PluginMetadata, PluginPropertyInt)
from citehound import CM
import pytest


class ImaginaryPlugin(PluginBase):
    sample_mandatory_prop = PluginPropertyInt()
    
    def __init__(self, citehound_manager=None):
        super().__init__(citehound_manager)
        self._description = PluginMetadata("Imaginary",
                                           "Imagine all the plugins...",
                                           "...launching all at once")

def test_pluginbase_metadata():
    """
    Every plugin carries metadata
    """

    u = ImaginaryPlugin()

    assert u.description.name == "Imaginary"
    assert u.description.short_desc == "Imagine all the plugins..."
    assert u.description.long_desc == "...launching all at once"

def test_pluginbase_userproperties():
    """
    Every plugin returns the right number and metadata for its user properties.
    """
    u = ImaginaryPlugin()

    assert len(u.user_properties) == 1
    assert type(u.user_properties) is dict
    assert len(u.user_properties["sample_mandatory_prop"]) == 3

def test_uninitialised_mandatory_props():
    """
    If a plugin is attempted to launch without mandatory parameters set, this should raise an exception.
    """
    u = ImaginaryPlugin(CM)

    # There is only one mandatory property in the imaginary plugin
    # which will cause a Typeerror exception

    with pytest.raises(ValueError):
        u()

    # Once this mandatory variable has received a valid value...
    u.sample_mandatory_prop = 42

    # Execution should proceed normally.
    assert u() is None

def test_pluginbase_reset():
    """
    Every plugin includes reset functionality to bring it back to its default
    state just after initialisation.
    """
    u = ImaginaryPlugin(CM)

    # There is only one mandatory property in the imaginary plugin
    # which will cause a Typeerror exception

    with pytest.raises(ValueError):
        u()

    # Once this mandatory variable has received a valid value...
    u.sample_mandatory_prop = 42

    # ...execution should proceed normally...
    assert u() is None

    # ...and once the plugin is reset...
    u.reset()

    # ...it should py failing again if the mandatory variables have not been set.
    with pytest.raises(ValueError):
        u()


