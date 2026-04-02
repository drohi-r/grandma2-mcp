"""
Edit Commands Tests

Tests for grandMA2 edit operation command generation.
Includes Edit, Copy, Move, Delete, and Remove command series.

Test Classes:
- TestEditCommands: Tests for edit keyword
- TestCopyCommands: Tests for copy, copy_cue
- TestMoveCommands: Tests for move
- TestDeleteCommands: Tests for delete series
- TestRemoveCommands: Tests for remove series
"""



class TestEditCommands:
    """
    Tests for Edit keyword commands.

    Edit is a function keyword used to modify values and open editors.
    Default behavior takes the first cue in the sequence of a selected executor.
    """

    # ---- Basic Edit ----

    def test_edit_no_args(self):
        """Test edit without arguments: edit"""
        from src.commands import edit

        result = edit()
        assert result == "edit"

    def test_edit_effect(self):
        """Test edit effect: edit effect 2"""
        from src.commands import edit

        result = edit("effect", 2)
        assert result == "edit effect 2"

    def test_edit_cue(self):
        """Test edit cue: edit cue 5"""
        from src.commands import edit

        result = edit("cue", 5)
        assert result == "edit cue 5"

    def test_edit_sequence(self):
        """Test edit sequence: edit sequence 1"""
        from src.commands import edit

        result = edit("sequence", 1)
        assert result == "edit sequence 1"

    def test_edit_group(self):
        """Test edit group: edit group 3"""
        from src.commands import edit

        result = edit("group", 3)
        assert result == "edit group 3"

    def test_edit_preset(self):
        """Test edit preset: edit preset 2.1"""
        from src.commands import edit

        result = edit("preset", "2.1")
        assert result == "edit preset 2.1"

    def test_edit_dmx_universe(self):
        """Test edit dmx universe: edit dmxuniverse 3"""
        from src.commands import edit

        result = edit("dmxuniverse", 3)
        assert result == "edit dmxuniverse 3"

    def test_edit_macro(self):
        """Test edit macro: edit macro 1"""
        from src.commands import edit

        result = edit("macro", 1)
        assert result == "edit macro 1"

    # ---- Edit with Range ----

    def test_edit_range(self):
        """Test edit with range: edit cue 1 thru 5"""
        from src.commands import edit

        result = edit("cue", 1, end=5)
        assert result == "edit cue 1 thru 5"

    # ---- Edit with List ----

    def test_edit_list(self):
        """Test edit with list: edit group 1 + 3 + 5"""
        from src.commands import edit

        result = edit("group", [1, 3, 5])
        assert result == "edit group 1 + 3 + 5"

    # ---- Edit with noconfirm Option ----

    def test_edit_with_noconfirm(self):
        """Test edit with noconfirm option: edit effect 2 /noconfirm"""
        from src.commands import edit

        result = edit("effect", 2, noconfirm=True)
        assert result == "edit effect 2 /noconfirm"

    def test_edit_range_with_noconfirm(self):
        """Test edit range with noconfirm: edit cue 1 thru 5 /noconfirm"""
        from src.commands import edit

        result = edit("cue", 1, end=5, noconfirm=True)
        assert result == "edit cue 1 thru 5 /noconfirm"


class TestCutCommands:
    """
    Tests for Cut keyword commands.

    Cut is a function used to specify the source objects for a two-step move action.
    The object list is temporarily stored for later use with Paste command.
    """

    # ---- Basic Cut ----

    def test_cut_preset(self):
        """Test cut preset: cut preset 4.1"""
        from src.commands import cut

        result = cut("preset", "4.1")
        assert result == "cut preset 4.1"

    def test_cut_group(self):
        """Test cut group: cut group 1"""
        from src.commands import cut

        result = cut("group", 1)
        assert result == "cut group 1"

    def test_cut_sequence(self):
        """Test cut sequence: cut sequence 5"""
        from src.commands import cut

        result = cut("sequence", 5)
        assert result == "cut sequence 5"

    def test_cut_macro(self):
        """Test cut macro: cut macro 10"""
        from src.commands import cut

        result = cut("macro", 10)
        assert result == "cut macro 10"

    # ---- Cut with Range ----

    def test_cut_range(self):
        """Test cut with range: cut group 1 thru 5"""
        from src.commands import cut

        result = cut("group", 1, end=5)
        assert result == "cut group 1 thru 5"

    # ---- Cut with List ----

    def test_cut_list(self):
        """Test cut with list: cut preset 4.1 + 4.2 + 4.3"""
        from src.commands import cut

        result = cut("preset", ["4.1", "4.2", "4.3"])
        assert result == "cut preset 4.1 + 4.2 + 4.3"


class TestPasteCommands:
    """
    Tests for Paste keyword commands.

    Paste is used to paste copied content from clipboard or move cut objects.
    """

    # ---- Basic Paste ----

    def test_paste_no_args(self):
        """Test paste without arguments: paste"""
        from src.commands import paste

        result = paste()
        assert result == "paste"

    def test_paste_cue(self):
        """Test paste to cue: paste 15"""
        from src.commands import paste

        result = paste(15)
        assert result == "paste 15"

    def test_paste_group(self):
        """Test paste to group: paste group 5"""
        from src.commands import paste

        result = paste("group", 5)
        assert result == "paste group 5"

    def test_paste_preset(self):
        """Test paste to preset: paste preset 4.5"""
        from src.commands import paste

        result = paste("preset", "4.5")
        assert result == "paste preset 4.5"

    def test_paste_sequence(self):
        """Test paste to sequence: paste sequence 10"""
        from src.commands import paste

        result = paste("sequence", 10)
        assert result == "paste sequence 10"


class TestCopyCommands:
    """Tests for Copy keyword commands."""

    # ---- Basic Copy ----

    def test_copy_single_to_target(self):
        """Test copy single object: copy group 1 at 5"""
        from src.commands import copy

        result = copy("group", 1, 5)
        assert result == "copy group 1 at 5"

    def test_copy_cue_to_target(self):
        """Test copy cue: copy cue 2 at 6"""
        from src.commands import copy

        result = copy("cue", 2, 6)
        assert result == "copy cue 2 at 6"

    def test_copy_macro_to_target(self):
        """Test copy macro: copy macro 2 at 6"""
        from src.commands import copy

        result = copy("macro", 2, 6)
        assert result == "copy macro 2 at 6"

    # ---- Copy to Clipboard ----

    def test_copy_to_clipboard(self):
        """Test copy to clipboard: copy cue 5"""
        from src.commands import copy

        result = copy("cue", 5)
        assert result == "copy cue 5"

    def test_copy_cue_to_clipboard(self):
        """Test copy_cue to clipboard: copy cue 5"""
        from src.commands import copy_cue

        result = copy_cue(5)
        assert result == "copy cue 5"

    # ---- Copy with Range (Thru) ----

    def test_copy_range_to_target(self):
        """Test copy range: copy group 1 thru 3 at 11"""
        from src.commands import copy

        result = copy("group", 1, 11, end=3)
        assert result == "copy group 1 thru 3 at 11"

    def test_copy_to_target_range(self):
        """Test copy to target range: copy group 2 at 6 thru 8"""
        from src.commands import copy

        result = copy("group", 2, 6, target_end=8)
        assert result == "copy group 2 at 6 thru 8"

    # ---- Copy with List ----

    def test_copy_list_to_target(self):
        """Test copy list: copy group 1 + 3 + 5 at 10"""
        from src.commands import copy

        result = copy("group", [1, 3, 5], 10)
        assert result == "copy group 1 + 3 + 5 at 10"

    def test_copy_to_target_list(self):
        """Test copy to target list: copy group 1 at 5 + 6 + 7"""
        from src.commands import copy

        result = copy("group", 1, [5, 6, 7])
        assert result == "copy group 1 at 5 + 6 + 7"

    # ---- Copy with Options ----

    def test_copy_with_overwrite(self):
        """Test copy with overwrite option."""
        from src.commands import copy

        result = copy("group", 1, 5, overwrite=True)
        assert result == "copy group 1 at 5 /overwrite"

    def test_copy_with_merge(self):
        """Test copy with merge option."""
        from src.commands import copy

        result = copy("cue", 1, 5, merge=True)
        assert result == "copy cue 1 at 5 /merge"

    def test_copy_with_noconfirm(self):
        """Test copy with noconfirm option."""
        from src.commands import copy

        result = copy("macro", 1, 5, noconfirm=True)
        assert result == "copy macro 1 at 5 /noconfirm"

    def test_copy_with_status(self):
        """Test copy with status option."""
        from src.commands import copy

        result = copy("cue", 1, 5, status=True)
        assert result == "copy cue 1 at 5 /status=true"

    def test_copy_with_cueonly(self):
        """Test copy with cueonly option."""
        from src.commands import copy

        result = copy("cue", 1, 5, cueonly=True)
        assert result == "copy cue 1 at 5 /cueonly=true"

    def test_copy_with_multiple_options(self):
        """Test copy with multiple options."""
        from src.commands import copy

        result = copy("cue", 1, 5, merge=True, noconfirm=True)
        assert result == "copy cue 1 at 5 /merge /noconfirm"

    # ---- copy_cue Convenience Function ----

    def test_copy_cue_basic(self):
        """Test copy_cue convenience function."""
        from src.commands import copy_cue

        result = copy_cue(2, 6)
        assert result == "copy cue 2 at 6"

    def test_copy_cue_with_range(self):
        """Test copy_cue with range."""
        from src.commands import copy_cue

        result = copy_cue(1, 10, end=5)
        assert result == "copy cue 1 thru 5 at 10"

    def test_copy_cue_with_options(self):
        """Test copy_cue with options."""
        from src.commands import copy_cue

        result = copy_cue(1, 10, overwrite=True, noconfirm=True)
        assert result == "copy cue 1 at 10 /overwrite /noconfirm"


class TestMoveCommands:
    """Tests for Move keyword commands."""

    # ---- Basic Move ----

    def test_move_single(self):
        """Test move single object: move group 5 at 9"""
        from src.commands import move

        result = move("group", 5, 9)
        assert result == "move group 5 at 9"

    def test_move_cue(self):
        """Test move cue: move cue 5 at 1"""
        from src.commands import move

        result = move("cue", 5, 1)
        assert result == "move cue 5 at 1"

    def test_move_preset(self):
        """Test move preset: move preset 3 at 10"""
        from src.commands import move

        result = move("preset", 3, 10)
        assert result == "move preset 3 at 10"

    # ---- Move with Range (Thru) ----

    def test_move_range(self):
        """Test move range: move group 1 thru 3 at 10"""
        from src.commands import move

        result = move("group", 1, 10, end=3)
        assert result == "move group 1 thru 3 at 10"

    def test_move_to_target_range(self):
        """Test move to target range: move group 1 at 10 thru 12"""
        from src.commands import move

        result = move("group", 1, 10, target_end=12)
        assert result == "move group 1 at 10 thru 12"

    # ---- Move with List ----

    def test_move_list_to_list(self):
        """Test move list to list: move preset 1 + 3 + 5 at 10 + 12 + 14"""
        from src.commands import move

        result = move("preset", [1, 3, 5], [10, 12, 14])
        assert result == "move preset 1 + 3 + 5 at 10 + 12 + 14"

    def test_move_list_to_single(self):
        """Test move list to single target: move group 1 + 2 + 3 at 10"""
        from src.commands import move

        result = move("group", [1, 2, 3], 10)
        assert result == "move group 1 + 2 + 3 at 10"


class TestDeleteCommands:
    """Tests for Delete keyword commands."""

    # ---- Generic Delete ----

    def test_delete_generic(self):
        """Test generic delete: delete cue 7"""
        from src.commands import delete

        result = delete("cue", 7)
        assert result == "delete cue 7"

    def test_delete_group(self):
        """Test delete group: delete group 3"""
        from src.commands import delete

        result = delete("group", 3)
        assert result == "delete group 3"

    def test_delete_fixture(self):
        """Test delete fixture (unpatch): delete fixture 4"""
        from src.commands import delete

        result = delete("fixture", 4)
        assert result == "delete fixture 4"

    def test_delete_world(self):
        """Test delete world: delete world 6"""
        from src.commands import delete

        result = delete("world", 6)
        assert result == "delete world 6"

    def test_delete_range(self):
        """Test delete range: delete cue 1 thru 5"""
        from src.commands import delete

        result = delete("cue", 1, end=5)
        assert result == "delete cue 1 thru 5"

    def test_delete_list(self):
        """Test delete list: delete group 1 + 3 + 5"""
        from src.commands import delete

        result = delete("group", [1, 3, 5])
        assert result == "delete group 1 + 3 + 5"

    def test_delete_with_noconfirm(self):
        """Test delete with noconfirm option."""
        from src.commands import delete

        result = delete("cue", 1, end=5, noconfirm=True)
        assert result == "delete cue 1 thru 5 /noconfirm"

    def test_delete_with_cueonly(self):
        """Test delete with cueonly option."""
        from src.commands import delete

        result = delete("cue", 3, cueonly=True)
        assert result == "delete cue 3 /cueonly"

    def test_delete_with_multiple_options(self):
        """Test delete with multiple options."""
        from src.commands import delete

        result = delete("cue", 1, deletevalues=True, cueonly=True, noconfirm=True)
        assert result == "delete cue 1 /deletevalues /cueonly /noconfirm"

    def test_delete_with_selection_filter(self):
        """Test delete with selection filter."""
        from src.commands import delete

        result = delete("cue", 5, selection_filter="fixture 1 thru 10")
        assert result == "delete cue 5 fixture 1 thru 10"

    # ---- Delete Cue Convenience ----

    def test_delete_cue_basic(self):
        """Test delete cue: delete cue 7"""
        from src.commands import delete_cue

        result = delete_cue(7)
        assert result == "delete cue 7"

    def test_delete_cue_with_sequence(self):
        """Test delete cue with sequence: delete cue 1 sequence 2"""
        from src.commands import delete_cue

        result = delete_cue(1, sequence_id=2)
        assert result == "delete cue 1 sequence 2"

    def test_delete_cue_range(self):
        """Test delete cue range: delete cue 1 thru 5"""
        from src.commands import delete_cue

        result = delete_cue(1, end=5)
        assert result == "delete cue 1 thru 5"

    def test_delete_cue_with_options(self):
        """Test delete cue with options."""
        from src.commands import delete_cue

        result = delete_cue(1, end=5, deletevalues=True, noconfirm=True)
        assert result == "delete cue 1 thru 5 /deletevalues /noconfirm"

    # ---- Delete Group Convenience ----

    def test_delete_group_basic(self):
        """Test delete group basic: delete group 3"""
        from src.commands import delete_group

        result = delete_group(3)
        assert result == "delete group 3"

    def test_delete_group_range(self):
        """Test delete group range: delete group 1 thru 5"""
        from src.commands import delete_group

        result = delete_group(1, end=5)
        assert result == "delete group 1 thru 5"

    def test_delete_group_with_noconfirm(self):
        """Test delete group with noconfirm."""
        from src.commands import delete_group

        result = delete_group(1, noconfirm=True)
        assert result == "delete group 1 /noconfirm"

    # ---- Delete Preset Convenience ----

    def test_delete_preset_by_name(self):
        """Test delete preset by name: delete preset 4.5 (color = presettype 4)"""
        from src.commands import delete_preset

        result = delete_preset("color", 5)
        assert result == "delete preset 4.5"

    def test_delete_preset_by_number(self):
        """Test delete preset by number: delete preset 1.1"""
        from src.commands import delete_preset

        result = delete_preset(1, 1)
        assert result == "delete preset 1.1"

    def test_delete_preset_range(self):
        """Test delete preset range: delete preset 1.1 thru 10"""
        from src.commands import delete_preset

        result = delete_preset(1, 1, end=10)
        assert result == "delete preset 1.1 thru 10"

    # ---- Delete Fixture Convenience ----

    def test_delete_fixture_basic(self):
        """Test delete fixture (unpatch): delete fixture 4"""
        from src.commands import delete_fixture

        result = delete_fixture(4)
        assert result == "delete fixture 4"

    def test_delete_fixture_range(self):
        """Test delete fixture range: delete fixture 1 thru 10"""
        from src.commands import delete_fixture

        result = delete_fixture(1, end=10)
        assert result == "delete fixture 1 thru 10"

    def test_delete_fixture_list(self):
        """Test delete fixture list: delete fixture 1 + 5 + 10"""
        from src.commands import delete_fixture

        result = delete_fixture([1, 5, 10])
        assert result == "delete fixture 1 + 5 + 10"

    # ---- Delete Messages ----

    def test_delete_messages(self):
        """Test delete messages: delete messages"""
        from src.commands import delete_messages

        result = delete_messages()
        assert result == "delete messages"


class TestRemoveCommands:
    """Tests for Remove keyword commands."""

    # ---- Generic Remove ----

    def test_remove_basic(self):
        """Test basic remove: remove"""
        from src.commands import remove

        result = remove()
        assert result == "remove"

    def test_remove_selection(self):
        """Test remove selection: remove selection"""
        from src.commands import remove

        result = remove("selection")
        assert result == "remove selection"

    def test_remove_fixture_with_id(self):
        """Test remove fixture: remove fixture 1"""
        from src.commands import remove

        result = remove("fixture", 1)
        assert result == "remove fixture 1"

    def test_remove_with_range(self):
        """Test remove with range: remove fixture 1 thru 10"""
        from src.commands import remove

        result = remove("fixture", 1, end=10)
        assert result == "remove fixture 1 thru 10"

    def test_remove_with_if_filter(self):
        """Test remove with if filter: remove fixture 1 if PresetType 1"""
        from src.commands import remove

        result = remove("fixture", 1, if_filter="PresetType 1")
        assert result == "remove fixture 1 if PresetType 1"

    def test_remove_presettype_quoted(self):
        """Test remove presettype: remove presettype "position" """
        from src.commands import remove

        result = remove("presettype", '"position"')
        assert result == 'remove presettype "position"'

    # ---- Remove Selection Convenience ----

    def test_remove_selection_convenience(self):
        """Test remove selection convenience: remove selection"""
        from src.commands import remove_selection

        result = remove_selection()
        assert result == "remove selection"

    # ---- Remove Preset Type Convenience ----

    def test_remove_preset_type_by_name(self):
        """Test remove preset type by name: remove presettype "position" """
        from src.commands import remove_preset_type

        result = remove_preset_type("position")
        assert result == 'remove presettype "position"'

    def test_remove_preset_type_by_number(self):
        """Test remove preset type by number: remove presettype 1"""
        from src.commands import remove_preset_type

        result = remove_preset_type(1)
        assert result == "remove presettype 1"

    def test_remove_preset_type_with_filter(self):
        """Test remove preset type with filter."""
        from src.commands import remove_preset_type

        result = remove_preset_type("color", if_filter="fixture 1 thru 10")
        assert result == 'remove presettype "color" if fixture 1 thru 10'

    # ---- Remove Fixture Convenience ----

    def test_remove_fixture_basic(self):
        """Test remove fixture: remove fixture 1"""
        from src.commands import remove_fixture

        result = remove_fixture(1)
        assert result == "remove fixture 1"

    def test_remove_fixture_range(self):
        """Test remove fixture range: remove fixture 1 thru 10"""
        from src.commands import remove_fixture

        result = remove_fixture(1, end=10)
        assert result == "remove fixture 1 thru 10"

    def test_remove_fixture_list(self):
        """Test remove fixture list: remove fixture 1 + 5 + 10"""
        from src.commands import remove_fixture

        result = remove_fixture([1, 5, 10])
        assert result == "remove fixture 1 + 5 + 10"

    def test_remove_fixture_with_if_filter(self):
        """Test remove fixture with if filter."""
        from src.commands import remove_fixture

        result = remove_fixture(1, if_filter="PresetType 1")
        assert result == "remove fixture 1 if PresetType 1"

    # ---- Remove Effect Convenience ----

    def test_remove_effect_basic(self):
        """Test remove effect: remove effect 1"""
        from src.commands import remove_effect

        result = remove_effect(1)
        assert result == "remove effect 1"

    def test_remove_effect_range(self):
        """Test remove effect range: remove effect 1 thru 5"""
        from src.commands import remove_effect

        result = remove_effect(1, end=5)
        assert result == "remove effect 1 thru 5"


class TestCloneCommands:
    """Tests for Clone keyword (DESTRUCTIVE)."""

    def test_clone_basic(self):
        from src.commands import clone
        assert clone("fixture", 1, 2) == "clone fixture 1 at 2"

    def test_clone_range(self):
        from src.commands import clone
        assert clone("fixture", 1, 10, end=5) == "clone fixture 1 thru 5 at 10"

    def test_clone_list(self):
        from src.commands import clone
        assert clone("fixture", [1, 3], [2, 4]) == "clone fixture 1 + 3 at 2 + 4"

    def test_clone_noconfirm(self):
        from src.commands import clone
        assert clone("fixture", 1, 2, noconfirm=True) == "clone fixture 1 at 2 /noconfirm"

    def test_clone_target_range(self):
        from src.commands import clone
        assert clone("fixture", 1, 10, target_end=15) == "clone fixture 1 at 10 thru 15"


class TestBlockUnblockCommands:
    """Tests for Block and Unblock keywords (DESTRUCTIVE)."""

    def test_block_basic(self):
        from src.commands import block
        assert block(5) == "block cue 5"

    def test_block_range(self):
        from src.commands import block
        assert block(1, end=5) == "block cue 1 thru 5"

    def test_block_with_sequence(self):
        from src.commands import block
        assert block(3, sequence_id=2) == "block cue 3 sequence 2"

    def test_unblock_basic(self):
        from src.commands import unblock
        assert unblock(5) == "unblock cue 5"

    def test_unblock_range(self):
        from src.commands import unblock
        assert unblock(1, end=5) == "unblock cue 1 thru 5"

    def test_unblock_with_sequence(self):
        from src.commands import unblock
        assert unblock(3, sequence_id=2) == "unblock cue 3 sequence 2"
