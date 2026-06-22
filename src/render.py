from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def render_html(sections: dict, date_str: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("email.html")
    return template.render(
        date=date_str,
        github=sections.get("github", []),
        blogs=sections.get("blogs", []),
        papers=sections.get("papers", []),
        failed_sources=sections.get("failed_sources", [])
    )
