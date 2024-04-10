import asyncio

from flask import Flask, jsonify, render_template, request
from jinja2 import Environment, FileSystemLoader
from selectolax.parser import HTMLParser

from database.methods import get_problems_by_exam_number

env = Environment(
    loader=FileSystemLoader("templates"), trim_blocks=True, lstrip_blocks=True, autoescape=True
)
app = Flask(__name__)


def remove_element_by_css_selector(html: str, css_selector: str) -> str:
    tree = HTMLParser(html=html)
    element = tree.css_first(css_selector)
    if element:
        element.decompose()
    return str(tree.body.html)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_problems", methods=["POST"])
def get_problems():
    exam_number = int(request.json["exam_number"])
    problems = asyncio.run(get_problems_by_exam_number(exam_number))
    problems = [
        remove_element_by_css_selector(i, "table > tbody > tr:nth-child(2)") for i in problems
    ]
    return jsonify(problems)


if __name__ == "__main__":
    app.run()  # noqa: S201
