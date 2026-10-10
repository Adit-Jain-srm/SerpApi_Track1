"""Teams message formatting."""
from models.tool_info import ToolInfo
from output.teams import format_tool_for_teams


def test_formatter_omits_duplicate_website_and_generic_features() -> None:
    same_url = ToolInfo(
        title="Nova",
        website="https://nova.example",
        source="https://nova.example",
        summary="Nova drafts launch notes.",
        features=["BPO Services", "Consultation", "Summarizes product launches"],
    )
    message = format_tool_for_teams(same_url, 1)
    assert "Website:" not in message
    assert "https://nova.example" in message
    assert "BPO Services" not in message
    assert "Consultation" not in message
    assert "Summarizes product launches" in message

    distinct = ToolInfo(
        title="Nova",
        website="https://nova.example",
        source="https://blog.example/nova",
        summary="Nova drafts launch notes.",
        features=["Summarizes product launches"],
    )
    assert "Website:" in format_tool_for_teams(distinct, 2)
