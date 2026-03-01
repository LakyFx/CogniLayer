"""CogniLayer TUI Dashboard — Main application."""

import sys
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-server"))

from tui.screens.overview import OverviewScreen
from tui.screens.facts import FactsScreen
from tui.screens.heatmap import HeatmapScreen
from tui.screens.clusters import ClustersScreen
from tui.screens.timeline import TimelineScreen
from tui.screens.gaps import GapsScreen
from tui.screens.contradictions import ContradictionsScreen


class CogniLayerTUI(App):
    """CogniLayer Memory Dashboard."""

    TITLE = "CogniLayer"
    SUB_TITLE = "Memory Dashboard"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("f5", "refresh", "Refresh"),
        ("1", "tab_1", "Overview"),
        ("2", "tab_2", "Facts"),
        ("3", "tab_3", "Heatmap"),
        ("4", "tab_4", "Clusters"),
        ("5", "tab_5", "Timeline"),
        ("6", "tab_6", "Gaps"),
        ("7", "tab_7", "Contradictions"),
    ]

    def __init__(self, project: str | None = None, **kwargs):
        self.project = project
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        title = f"CogniLayer — {self.project}" if self.project else "CogniLayer — All Projects"
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Overview", id="tab-overview"):
                yield OverviewScreen(project=self.project)
            with TabPane("Facts", id="tab-facts"):
                yield FactsScreen(project=self.project)
            with TabPane("Heatmap", id="tab-heatmap"):
                yield HeatmapScreen(project=self.project)
            with TabPane("Clusters", id="tab-clusters"):
                yield ClustersScreen(project=self.project)
            with TabPane("Timeline", id="tab-timeline"):
                yield TimelineScreen(project=self.project)
            with TabPane("Gaps", id="tab-gaps"):
                yield GapsScreen(project=self.project)
            with TabPane("Contradictions", id="tab-contradictions"):
                yield ContradictionsScreen(project=self.project)
        yield Footer()

    def action_tab_1(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-overview"

    def action_tab_2(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-facts"

    def action_tab_3(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-heatmap"

    def action_tab_4(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-clusters"

    def action_tab_5(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-timeline"

    def action_tab_6(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-gaps"

    def action_tab_7(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab-contradictions"

    def action_refresh(self) -> None:
        """Refresh by remounting the active tab content."""
        self.notify("Refreshing...", severity="information")
        # Simple approach: exit and re-run
        # For now just notify — full refresh would require remounting widgets


if __name__ == "__main__":
    project = None
    demo_mode = "--demo" in sys.argv

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--project" and i < len(sys.argv) - 1:
            project = sys.argv[i + 1]

    if demo_mode:
        from tui.demo import create_demo_db
        import tui.data as data_module
        demo_path = create_demo_db()
        data_module.DB_PATH = Path(demo_path)

    app = CogniLayerTUI(project=project)
    app.run()

    # Cleanup demo DB
    if demo_mode:
        try:
            Path(demo_path).unlink(missing_ok=True)
        except Exception:
            pass
