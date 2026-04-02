"""
Attribute, Feature, and PresetType Keywords Tests

Tests for grandMA2 Attribute object type command generation.

Attribute:
- Object type used as reference to fixture attributes
- Can be called by name (string) or number
- Organized by Features, which are organized by PresetType

Feature:
- Container for related attributes
- Can use dot notation to access specific attribute

PresetType:
- Container for related features
- Can use dot notation to access feature and attribute

Test Classes:
- TestAttribute: Tests for Attribute object reference
- TestFeature: Tests for Feature object reference
- TestPresetType: Tests for PresetType object reference
"""



class TestAttribute:
    """
    Tests for Attribute keyword - reference fixture attributes.

    Syntax:
        Attribute "Name"
        Attribute [number]
    """

    # ---- Attribute by name ----

    def test_attribute_by_name(self):
        """Test attribute by name: attribute "pan" """
        from src.commands import attribute

        result = attribute("pan")
        assert result == 'attribute "pan"'

    def test_attribute_by_name_tilt(self):
        """Test attribute by name: attribute "tilt" """
        from src.commands import attribute

        result = attribute("tilt")
        assert result == 'attribute "tilt"'

    def test_attribute_by_name_dimmer(self):
        """Test attribute by name: attribute "dimmer" """
        from src.commands import attribute

        result = attribute("dimmer")
        assert result == 'attribute "dimmer"'

    # ---- Attribute by number ----

    def test_attribute_by_number(self):
        """Test attribute by number: attribute 1"""
        from src.commands import attribute

        result = attribute(1)
        assert result == "attribute 1"

    def test_attribute_by_number_larger(self):
        """Test attribute by larger number: attribute 5"""
        from src.commands import attribute

        result = attribute(5)
        assert result == "attribute 5"


class TestFeature:
    """
    Tests for Feature keyword - reference feature groups.

    Syntax:
        Feature [number]
        Feature "Name"
        Feature [Feature].[Attribute]
        Feature "Name".[Attribute]
        Feature $variable.[Attribute]
    """

    # ---- Feature by number ----

    def test_feature_by_number(self):
        """Test feature by number: feature 3"""
        from src.commands import feature

        result = feature(3)
        assert result == "feature 3"

    def test_feature_by_number_2(self):
        """Test feature by number: feature 2"""
        from src.commands import feature

        result = feature(2)
        assert result == "feature 2"

    # ---- Feature by name (quoted) ----

    def test_feature_by_name(self):
        """Test feature by name: feature "Gobo1" """
        from src.commands import feature

        result = feature("Gobo1")
        assert result == 'feature "Gobo1"'

    def test_feature_by_name_position(self):
        """Test feature by name: feature "Position" """
        from src.commands import feature

        result = feature("Position")
        assert result == 'feature "Position"'

    # ---- Feature with attribute (dot notation) ----

    def test_feature_with_attribute(self):
        """Test feature with attribute: feature 3.1"""
        from src.commands import feature

        result = feature(3, 1)
        assert result == "feature 3.1"

    def test_feature_with_attribute_different_numbers(self):
        """Test feature with attribute: feature 2.5"""
        from src.commands import feature

        result = feature(2, 5)
        assert result == "feature 2.5"

    # ---- Feature name with attribute (dot notation) ----

    def test_feature_name_with_attribute(self):
        """Test feature name with attribute: feature "Position".2"""
        from src.commands import feature

        result = feature("Position", 2)
        assert result == 'feature "Position".2'

    def test_feature_name_with_attribute_gobo(self):
        """Test feature name with attribute: feature "Gobo1".1"""
        from src.commands import feature

        result = feature("Gobo1", 1)
        assert result == 'feature "Gobo1".1'

    # ---- Feature with variable ----

    def test_feature_with_variable(self):
        """Test feature with variable: feature $feature.1"""
        from src.commands import feature

        result = feature("$feature", 1)
        assert result == "feature $feature.1"

    def test_feature_with_variable_2(self):
        """Test feature with variable: feature $feature.2"""
        from src.commands import feature

        result = feature("$feature", 2)
        assert result == "feature $feature.2"


class TestPresetType:
    """
    Tests for PresetType keyword - reference preset type groups.

    Note: preset_type function already exists in the codebase.
    These tests verify it works with feature and attribute parameters.

    Syntax:
        PresetType [number]
        PresetType [type].[feature]
        PresetType [type].[feature].[attribute]
    """

    # ---- PresetType by number ----

    def test_preset_type_by_number(self):
        """Test preset type by number: presettype 3"""
        from src.commands import preset_type

        result = preset_type(3)
        assert result == "presettype 3"

    # ---- PresetType with feature (using keyword arg) ----

    def test_preset_type_with_feature(self):
        """Test preset type with feature: presettype 3.2"""
        from src.commands import preset_type

        result = preset_type(3, feature=2)
        assert result == "presettype 3.2"

    # ---- PresetType with feature and attribute (using keyword args) ----

    def test_preset_type_with_feature_and_attribute(self):
        """Test preset type with feature and attribute: presettype 3.2.1"""
        from src.commands import preset_type

        result = preset_type(3, feature=2, attribute=1)
        assert result == "presettype 3.2.1"

    def test_preset_type_full_path(self):
        """Test preset type full path: presettype 1.3.5"""
        from src.commands import preset_type

        result = preset_type(1, feature=3, attribute=5)
        assert result == "presettype 1.3.5"
