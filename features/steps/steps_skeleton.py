from behave import given, when, then, use_step_matcher
import re

use_step_matcher("re")


def _append_step_line(context, keyword: str, text: str):
    if not hasattr(context, "gherkin_steps"):
        context.gherkin_steps = []
    context.gherkin_steps.append({"keyword": keyword, "text": text})


def _append_docstring_if_any(context):
    if getattr(context, "text", None):
        if not hasattr(context, "gherkin_docstrings"):
            context.gherkin_docstrings = []
        context.gherkin_docstrings.append(context.text)


# Catch-all GIVEN
@given(r"^(?P<text>.+)$")
def step_any_given(context, text):
    _append_step_line(context, "Given", text)
    _append_docstring_if_any(context)


# Catch-all WHEN
@when(r"^(?P<text>.+)$")
def step_any_when(context, text):
    _append_step_line(context, "When", text)
    _append_docstring_if_any(context)


# Catch-all THEN
@then(r"^(?P<text>.+)$")
def step_any_then(context, text):
    _append_step_line(context, "Then", text)
    _append_docstring_if_any(context)