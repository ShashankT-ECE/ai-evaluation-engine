"""
LLM-based rubric grader using the Google Gemini API.
"""

import json
import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_MODEL_NAME = "gemini-2.5-flash"

_RUBRIC_PROMPT_TEMPLATE = """\
You are a strict code quality evaluator. Evaluate the following Python source code \
against the rubric below. Return ONLY a valid JSON object — no markdown fences, \
no extra text, nothing else.

RUBRIC (each criterion is worth up to ~3.3 points, total out of 10):
1. Single Responsibility Principle: Does each class/function do exactly one thing?
2. Descriptive Variable Names: Are all variable and parameter names self-documenting \
and unambiguous?
3. No Magic Numbers: Are all numeric constants named or passed as parameters rather \
than hardcoded inline?

SOURCE CODE TO EVALUATE:
```python
{source_code}
```

Required output format (strict JSON, no markdown):
{{"score": <integer 0-10>, "reasoning": "<one or two sentence explanation>"}}
"""


def evaluate_code_with_llm(source_code_path: str) -> dict:
    """
    Read *source_code_path*, send it to Gemini for rubric evaluation, and
    return a dict with keys ``score`` (int) and ``reasoning`` (str).

    Raises:
        EnvironmentError: if GEMINI_API_KEY is not set.
        ValueError: if the model returns unparseable JSON.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    genai.configure(api_key=api_key)

    with open(source_code_path, "r", encoding="utf-8") as source_file:
        source_code = source_file.read()

    prompt = _RUBRIC_PROMPT_TEMPLATE.format(source_code=source_code)

    model = genai.GenerativeModel(model_name=_MODEL_NAME)
    response = model.generate_content(prompt)

    raw_text = response.text.strip()

    # Strip accidental markdown fences the model might still produce
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as parse_error:
        raise ValueError(
            f"Gemini returned non-JSON output:\n{raw_text}"
        ) from parse_error

    if "score" not in result or "reasoning" not in result:
        raise ValueError(
            f"JSON response is missing required keys. Got: {result}"
        )

    result["score"] = int(result["score"])
    return result


if __name__ == "__main__":
    import pathlib

    submission = pathlib.Path(__file__).parent.parent / "submissions" / "dummy_ai_submission.py"
    evaluation = evaluate_code_with_llm(str(submission))
    print(f"Score    : {evaluation['score']} / 10")
    print(f"Reasoning: {evaluation['reasoning']}")
