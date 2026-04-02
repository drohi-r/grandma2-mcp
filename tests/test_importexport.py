"""
Import/Export Command Builder Tests

Live-validated on grandMA2 onPC 3.9.60.65.
"""

from src.commands.functions.importexport import (
    export_object,
    import_fixture_type_cmd,
    import_layer_cmd,
    import_object,
)


class TestExportObjectBuilder:
    def test_basic(self):
        assert export_object("Group", 1, "mygroups") == 'export Group 1 "mygroups"'

    def test_no_id(self):
        assert export_object("Macro", None, "all_macros") == 'export Macro "all_macros"'

    def test_range(self):
        assert export_object("Macro", "1 thru 5", "macros") == 'export Macro 1 thru 5 "macros"'

    def test_preset_ref(self):
        assert export_object("Preset", "1.3", "dim3") == 'export Preset 1.3 "dim3"'

    def test_preset_type_all(self):
        assert export_object("Preset", "1", "all_dimmer") == 'export Preset 1 "all_dimmer"'

    def test_overwrite(self):
        assert export_object("Group", 1, "grp", overwrite=True) == 'export Group 1 "grp" /overwrite'

    def test_noconfirm(self):
        assert export_object("Sequence", 2, "seq2", noconfirm=True) == 'export Sequence 2 "seq2" /noconfirm'

    def test_style_csv(self):
        assert export_object("Sequence", None, "seqs", style="csv") == 'export Sequence "seqs" /style=csv'

    def test_style_html(self):
        assert export_object("Group", 3, "grp3", style="html") == 'export Group 3 "grp3" /style=html'

    def test_all_flags(self):
        result = export_object("Macro", "1 thru 5", "macros", overwrite=True, noconfirm=True, style="csv")
        assert result == 'export Macro 1 thru 5 "macros" /overwrite /noconfirm /style=csv'

    def test_userprofile_by_name(self):
        assert export_object("UserProfile", '"administrator"', "admin_profile") == \
            'export UserProfile "administrator" "admin_profile"'

    def test_no_filename(self):
        assert export_object("Group", 1) == "export Group 1"

    def test_no_id_no_filename(self):
        assert export_object("Macro") == "export Macro"


class TestImportObjectBuilder:
    def test_basic_with_id(self):
        assert import_object("mygroups", "Group", 5) == 'import "mygroups" at Group 5'

    def test_no_id(self):
        assert import_object("macros", "Macro") == 'import "macros" at Macro'

    def test_preset_ref(self):
        assert import_object("preset_dimmer", "Preset", "1.99") == 'import "preset_dimmer" at Preset 1.99'

    def test_noconfirm(self):
        assert import_object("show", "Group", 1, noconfirm=True) == 'import "show" at Group 1 /noconfirm'

    def test_quiet(self):
        assert import_object("show", "Group", 10, quiet=True) == 'import "show" at Group 10 /quiet'

    def test_all_flags(self):
        result = import_object("fixtures", "Macro", 1, noconfirm=True, quiet=True)
        assert result == 'import "fixtures" at Macro 1 /noconfirm /quiet'

    def test_matricks(self):
        assert import_object("matricks_test", "MAtricks", 99) == 'import "matricks_test" at MAtricks 99'

    def test_mask(self):
        assert import_object("mask_test", "Mask", 5) == 'import "mask_test" at Mask 5'


class TestImportFixtureTypeCmdBuilder:
    def test_basic(self):
        assert import_fixture_type_cmd("Martin", "Mac700Profile_Extended", "Extended") == \
            'Import "Martin@Mac700Profile_Extended@Extended"'

    def test_generic_dimmer(self):
        assert import_fixture_type_cmd("Generic", "Dimmer", "Mode 1") == \
            'Import "Generic@Dimmer@Mode 1"'

    def test_at_signs_in_key(self):
        result = import_fixture_type_cmd("A", "B", "C")
        assert result == 'Import "A@B@C"'
        assert result.count("@") == 2


class TestImportLayerCmdBuilder:
    def test_no_index(self):
        assert import_layer_cmd("dimmers") == 'Import "dimmers"'

    def test_with_index(self):
        assert import_layer_cmd("mac700s", 2) == 'Import "mac700s" At 2'

    def test_index_one(self):
        assert import_layer_cmd("my_fixtures", 1) == 'Import "my_fixtures" At 1'

    def test_filename_with_spaces(self):
        assert import_layer_cmd("my layer file", 3) == 'Import "my layer file" At 3'
