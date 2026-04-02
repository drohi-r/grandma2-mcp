"""Append import/export tool tests to test_tools.py"""
import textwrap

tests = textwrap.dedent('''


    # ============================================================
    # Tests for Tools 53-54 -- Import / Export
    # ============================================================


class TestExportObjectsTool:
    @pytest.mark.asyncio
    async def test_export_blocked(self):
        from src.server import export_objects
        result = await export_objects(object_type="Group", object_id="1", filename="test")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_basic(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Group", object_id="1", filename="my_groups", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'export Group 1 "my_groups" /noconfirm'
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_range(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Macro", object_id="1 thru 5", filename="macros", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'export Macro 1 thru 5 "macros" /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_preset(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Preset", object_id="1.3", filename="dim3", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'export Preset 1.3 "dim3" /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_with_style_csv(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Sequence", object_id="1", filename="seqs", style="csv", confirm_destructive=True)
        data = json.loads(result)
        assert "/style=csv" in data["command_sent"]

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_export_with_overwrite(self, mock_get_client):
        from src.server import export_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await export_objects(object_type="Group", object_id="1", filename="grp", overwrite=True, confirm_destructive=True)
        data = json.loads(result)
        assert "/overwrite" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_export_invalid_type(self):
        from src.server import export_objects
        result = await export_objects(object_type="Banana", object_id="1", filename="test", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
        assert "Banana" in data["error"]

    @pytest.mark.asyncio
    async def test_export_invalid_style(self):
        from src.server import export_objects
        result = await export_objects(object_type="Group", object_id="1", filename="test", style="pdf", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
        assert "style" in data["error"]


class TestImportObjectsTool:
    @pytest.mark.asyncio
    async def test_import_blocked(self):
        from src.server import import_objects
        result = await import_objects(filename="my_groups", destination_type="Group")
        data = json.loads(result)
        assert data["blocked"] is True
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_basic(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="1 object(s) imported.")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="my_groups", destination_type="Group", destination_id="99", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "my_groups" at Group 99 /noconfirm'
        assert data["risk_tier"] == "DESTRUCTIVE"

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_no_id(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="macros", destination_type="Macro", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "macros" at Macro /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_preset(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="preset_dimmer", destination_type="Preset", destination_id="1.99", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "preset_dimmer" at Preset 1.99 /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_matricks(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="matricks_test", destination_type="MAtricks", destination_id="99", confirm_destructive=True)
        data = json.loads(result)
        assert data["command_sent"] == 'import "matricks_test" at MAtricks 99 /noconfirm'

    @pytest.mark.asyncio
    @patch("src.server.get_client")
    async def test_import_with_quiet(self, mock_get_client):
        from src.server import import_objects
        mock_client = MagicMock()
        mock_client.send_command_with_response = AsyncMock(return_value="Ok")
        mock_get_client.return_value = mock_client
        result = await import_objects(filename="show_backup", destination_type="Group", destination_id="10", quiet=True, confirm_destructive=True)
        data = json.loads(result)
        assert "/quiet" in data["command_sent"]

    @pytest.mark.asyncio
    async def test_import_invalid_type(self):
        from src.server import import_objects
        result = await import_objects(filename="test", destination_type="Banana", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
        assert "Banana" in data["error"]

    @pytest.mark.asyncio
    async def test_import_screen_rejected(self):
        from src.server import import_objects
        result = await import_objects(filename="screen_test", destination_type="Screen", confirm_destructive=True)
        data = json.loads(result)
        assert "error" in data
''')

with open(r'C:\Users\romar\ma2-onPC-mcp\tests\test_tools.py', 'a', encoding='utf-8') as f:
    f.write(tests)
print("Done — appended TestExportObjectsTool and TestImportObjectsTool")
