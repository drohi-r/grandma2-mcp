"""
Tests for Variable Function Keywords

Variable keywords are used to set and modify show/user variables.

SetUserVar (SetUs) - Set user profile specific variables
SetVar (SetV) - Set global show variables
AddUserVar (AddU) - Change/extend user variable content
AddVar (Ad) - Change/extend show variable content

Syntax:
    SetUserVar $variablename = numericvalue
    SetUserVar $variablename = "text"
    SetUserVar $variablename = ("text")  # Input dialog
    SetUserVar $variablename = nothing   # Delete variable

    AddUserVar $variablename = numericvalue
    AddUserVar $variablename = "text"
"""



class TestSetUserVar:
    """
    Tests for SetUserVar keyword - set user profile specific variables.

    Syntax:
        SetUserVar $variablename = numericvalue
        SetUserVar $variablename = "text"
        SetUserVar $variablename = ("text")
        SetUserVar $variablename = nothing
    """

    def test_set_user_var_numeric(self):
        """Test set user var with numeric value: setuservar $mycounter = 5"""
        from src.commands import set_user_var

        result = set_user_var("$mycounter", 5)
        assert result == "setuservar $mycounter = 5"

    def test_set_user_var_text(self):
        """Test set user var with text: setuservar $myname = "John" """
        from src.commands import set_user_var

        result = set_user_var("$myname", "John")
        assert result == 'setuservar $myname = "John"'

    def test_set_user_var_input_dialog(self):
        """Test set user var with input dialog: setuservar $CueNumber = ("Cue number to store?")"""
        from src.commands import set_user_var

        result = set_user_var("$CueNumber", "Cue number to store?", input_dialog=True)
        assert result == 'setuservar $CueNumber = ("Cue number to store?")'

    def test_set_user_var_delete(self):
        """Test delete user var: setuservar $CueNumber = """
        from src.commands import set_user_var

        result = set_user_var("$CueNumber", None)
        assert result == "setuservar $CueNumber ="


class TestSetVar:
    """
    Tests for SetVar keyword - set global show variables.

    Syntax:
        SetVar $variablename = numericvalue
        SetVar $variablename = "text"
        SetVar $variablename = ("text")
        SetVar $variablename = nothing
    """

    def test_set_var_numeric(self):
        """Test set var with numeric value: setvar $mycounter = 5"""
        from src.commands import set_var

        result = set_var("$mycounter", 5)
        assert result == "setvar $mycounter = 5"

    def test_set_var_text(self):
        """Test set var with text: setvar $myname = "John" """
        from src.commands import set_var

        result = set_var("$myname", "John")
        assert result == 'setvar $myname = "John"'

    def test_set_var_input_dialog(self):
        """Test set var with input dialog: setvar $Songname = ("Which song?")"""
        from src.commands import set_var

        result = set_var("$Songname", "Which song?", input_dialog=True)
        assert result == 'setvar $Songname = ("Which song?")'

    def test_set_var_delete(self):
        """Test delete var: setvar $CueNumber = """
        from src.commands import set_var

        result = set_var("$CueNumber", None)
        assert result == "setvar $CueNumber ="


class TestAddUserVar:
    """
    Tests for AddUserVar keyword - change/extend user variable content.

    Syntax:
        AddUserVar $variablename = numericvalue
        AddUserVar $variablename = "text"
    """

    def test_add_user_var_numeric(self):
        """Test add user var with numeric: adduservar $mycounter = 6"""
        from src.commands import add_user_var

        result = add_user_var("$mycounter", 6)
        assert result == "adduservar $mycounter = 6"

    def test_add_user_var_text(self):
        """Test add user var with text: adduservar $myname = " Doe" """
        from src.commands import add_user_var

        result = add_user_var("$myname", " Doe")
        assert result == 'adduservar $myname = " Doe"'


class TestAddVar:
    """
    Tests for AddVar keyword - change/extend show variable content.

    Syntax:
        AddVar $variablename = numericvalue
        AddVar $variablename = "text"
    """

    def test_add_var_numeric(self):
        """Test add var with numeric: addvar $mycounter = 6"""
        from src.commands import add_var

        result = add_var("$mycounter", 6)
        assert result == "addvar $mycounter = 6"

    def test_add_var_text(self):
        """Test add var with text: addvar $myname = " Doe" """
        from src.commands import add_var

        result = add_var("$myname", " Doe")
        assert result == 'addvar $myname = " Doe"'

