from citehound.plugin import (PluginBase, PluginPropertyInt, PluginPropertyFloat, 
                       PluginPropertyString, PluginPropertyRegex, PluginPropertyMapped)


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
    optional_bounded_quant_string = PluginPropertyString(default_value="White", choices={"White":"White", "Black":"Black"})

    optional_regex = PluginPropertyRegex(default_value="SOME_VAR", expression="[A-Z_][A-Z_]*")

    optional_mapped = PluginPropertyMapped(default_value="no")


# Tests covering the property initialisation

def test_init_metadata():
    u = ImaginaryPlugin()

    user_properties = u.user_properties

    assert user_properties["unbounded_optional_int"]["prompt"] == "Enter an integer"

    
