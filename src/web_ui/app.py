import asyncio
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from jinja2 import Environment, FileSystemLoader
from selectolax.parser import HTMLParser

from src.database.methods import get_problems_by_exam_number
from src.misc import PathControl

env = Environment(
    loader=FileSystemLoader(PathControl.get(str(Path("web_ui") / "templates"))),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=True,
)

main_page_template = env.get_template("index.html")
app = Flask(__name__)


def remove_element_by_css_selector(html: str, css_selector: str) -> str:
    tree = HTMLParser(html=html)
    element = tree.css_first(css_selector)
    if element:
        element.decompose()
    return str(tree.body.html)


@app.route("/")
def index():
    return main_page_template.render()


@app.route("/get_problems", methods=["POST"])
def get_problems():
    exam_number = int(request.json["exam_number"])
    print(f"{exam_number=}")
    problems_data = asyncio.run(get_problems_by_exam_number(exam_number))
    problem_htmls = [i.condition_html for i in problems_data]

    problems = [
        remove_element_by_css_selector(i, "table > tbody > tr:nth-child(2)") for i in problem_htmls
    ]  # removing the response input field
    return jsonify(problems)


@app.route("/robots.txt")
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


if __name__ == "__main__":
    app.run(port=3636, debug=False)
