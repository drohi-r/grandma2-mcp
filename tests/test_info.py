"""
Info Commands Tests

Tests for grandMA2 information query command generation.
Includes List and Info command series.

Test Classes:
- TestListCommands: Tests for list_objects, list_cue, list_group, list_preset,
                    list_attribute, list_messages
- TestInfoCommands: Tests for info, info_group, info_cue, info_preset
"""



class TestListCommands:
    """Tests for List keyword commands."""

    # ---- Generic List ----

    def test_list_objects_cue(self):
        """Test list cue: list cue"""
        from src.commands import list_objects

        result = list_objects("cue")
        assert result == "list cue"

    def test_list_objects_group_range(self):
        """Test list group range: list group thru 10"""
        from src.commands import list_objects

        result = list_objects("group", end=10)
        assert result == "list group thru 10"

    def test_list_objects_attribute(self):
        """Test list attribute: list attribute"""
        from src.commands import list_objects

        result = list_objects("attribute")
        assert result == "list attribute"

    def test_list_objects_with_filename(self):
        """Test list with filename option."""
        from src.commands import list_objects

        result = list_objects("group", filename="my_groups")
        assert result == "list group /filename=my_groups"

    def test_list_objects_empty(self):
        """Test list without object type: list"""
        from src.commands import list_objects

        result = list_objects()
        assert result == "list"

    # ---- List Cue Convenience ----

    def test_list_cue_basic(self):
        """Test list cue: list cue"""
        from src.commands import list_cue

        result = list_cue()
        assert result == "list cue"

    def test_list_cue_range(self):
        """Test list cue range: list cue 1 thru 10"""
        from src.commands import list_cue

        result = list_cue(1, end=10)
        assert result == "list cue 1 thru 10"

    def test_list_cue_with_sequence(self):
        """Test list cue with sequence: list cue sequence 5"""
        from src.commands import list_cue

        result = list_cue(sequence_id=5)
        assert result == "list cue sequence 5"

    def test_list_cue_with_filename(self):
        """Test list cue with filename."""
        from src.commands import list_cue

        result = list_cue(filename="cue_list")
        assert result == "list cue /filename=cue_list"

    # ---- List Group Convenience ----

    def test_list_group_basic(self):
        """Test list group: list group"""
        from src.commands import list_group

        result = list_group()
        assert result == "list group"

    def test_list_group_range(self):
        """Test list group range: list group thru 10"""
        from src.commands import list_group

        result = list_group(end=10)
        assert result == "list group thru 10"

    def test_list_group_specific_range(self):
        """Test list group specific range: list group 1 thru 5"""
        from src.commands import list_group

        result = list_group(1, end=5)
        assert result == "list group 1 thru 5"

    # ---- List Preset Convenience ----

    def test_list_preset_basic(self):
        """Test list preset: list preset"""
        from src.commands import list_preset

        result = list_preset()
        assert result == "list preset"

    def test_list_preset_by_type(self):
        """Test list preset by type: list preset "color" """
        from src.commands import list_preset

        result = list_preset("color")
        assert result == 'list preset "color"'

    def test_list_preset_with_wildcard(self):
        """Test list preset with wildcard: list preset "color"."m*" """
        from src.commands import list_preset

        result = list_preset("color", '"m*"')
        assert result == 'list preset "color"."m*"'

    def test_list_preset_numeric_type_with_wildcard(self):
        """Test list preset with numeric type: list preset 4."m*" """
        from src.commands import list_preset

        result = list_preset(4, '"m*"')
        assert result == 'list preset 4."m*"'

    # ---- List Attribute Convenience ----

    def test_list_attribute_basic(self):
        """Test list attribute: list attribute"""
        from src.commands import list_attribute

        result = list_attribute()
        assert result == "list attribute"

    def test_list_attribute_with_filename(self):
        """Test list attribute with filename."""
        from src.commands import list_attribute

        result = list_attribute(filename="attrs")
        assert result == "list attribute /filename=attrs"

    # ---- List Messages Convenience ----

    def test_list_messages_basic(self):
        """Test list messages: list messages"""
        from src.commands import list_messages

        result = list_messages()
        assert result == "list messages"

    def test_list_messages_with_condition(self):
        """Test list messages with condition."""
        from src.commands import list_messages

        result = list_messages(condition="error")
        assert result == "list messages /condition=error"


class TestInfoCommands:
    """Tests for Info keyword commands."""

    # ---- Generic Info ----

    def test_info_display(self):
        """Test info display: info group 3"""
        from src.commands import info

        result = info("group", 3)
        assert result == "info group 3"

    def test_info_add_text(self):
        """Test info add text: info group 3 "some text" """
        from src.commands import info

        result = info("group", 3, text="these fixtures are in the back truss")
        assert result == 'info group 3 "these fixtures are in the back truss"'

    def test_info_range(self):
        """Test info range: info cue 1 thru 5"""
        from src.commands import info

        result = info("cue", 1, end=5)
        assert result == "info cue 1 thru 5"

    # ---- Info Group Convenience ----

    def test_info_group_display(self):
        """Test info group display: info group 3"""
        from src.commands import info_group

        result = info_group(3)
        assert result == "info group 3"

    def test_info_group_add_text(self):
        """Test info group add text."""
        from src.commands import info_group

        result = info_group(3, text="main stage fixtures")
        assert result == 'info group 3 "main stage fixtures"'

    def test_info_group_range(self):
        """Test info group range: info group 1 thru 5"""
        from src.commands import info_group

        result = info_group(1, end=5)
        assert result == "info group 1 thru 5"

    # ---- Info Cue Convenience ----

    def test_info_cue_display(self):
        """Test info cue display: info cue 5"""
        from src.commands import info_cue

        result = info_cue(5)
        assert result == "info cue 5"

    def test_info_cue_with_sequence(self):
        """Test info cue with sequence: info cue 5 sequence 2"""
        from src.commands import info_cue

        result = info_cue(5, sequence_id=2)
        assert result == "info cue 5 sequence 2"

    def test_info_cue_add_text(self):
        """Test info cue add text."""
        from src.commands import info_cue

        result = info_cue(1, text="opening look")
        assert result == 'info cue 1 "opening look"'

    def test_info_cue_range(self):
        """Test info cue range: info cue 1 thru 10"""
        from src.commands import info_cue

        result = info_cue(1, end=10)
        assert result == "info cue 1 thru 10"

    # ---- Info Preset Convenience ----

    def test_info_preset_display(self):
        """Test info preset display: info preset 4.5"""
        from src.commands import info_preset

        result = info_preset(4, 5)
        assert result == "info preset 4.5"

    def test_info_preset_by_name(self):
        """Test info preset by name: info preset 4.1 (color=4)"""
        from src.commands import info_preset

        result = info_preset("color", 1)
        assert result == "info preset 4.1"

    def test_info_preset_add_text(self):
        """Test info preset add text."""
        from src.commands import info_preset

        result = info_preset(4, 5, text="deep blue")
        assert result == 'info preset 4.5 "deep blue"'


class TestListSpecializedBuilders:
    """Tests for list_plugin_library, list_fader_modules, list_update."""

    def test_list_plugin_library(self):
        from src.commands import list_plugin_library
        assert list_plugin_library() == "listpluginlibrary"

    def test_list_fader_modules(self):
        from src.commands import list_fader_modules
        assert list_fader_modules() == "listfadermodules"

    def test_list_update(self):
        from src.commands import list_update
        assert list_update() == "listupdate"
