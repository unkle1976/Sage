"""Rule checks and Claude judge for Sage conversation evaluation."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.garden import Garden
from app.models.plant import Plant
from app.models.plant_spec import PlantSpec
from app.models.user import User
from app.eval.personas import Persona

logger = logging.getLogger(__name__)

JUDGE_MODEL = "claude-sonnet-4-20250514"


@dataclass
class EvalResult:
    persona_name: str
    turns_completed: int
    transcript: list[dict] = field(default_factory=list)  # [{"role": "user"|"sage", "content": str}]
    rule_results: dict = field(default_factory=dict)
    rule_passed: bool = False
    judge_scores: dict | None = None
    judge_average: float | None = None
    errors: list[str] = field(default_factory=list)


async def check_onboarding_complete(user: User) -> bool:
    """Check that the user completed onboarding."""
    return bool(user.onboarding_complete)


async def check_plants_created(
    user_id, session: AsyncSession, expected_plants: list[str]
) -> tuple[bool, list[str]]:
    """Check that Plant records exist with matching PlantSpec names.

    Returns (passed, list_of_matched_plant_names).
    """
    if not expected_plants:
        return True, []

    stmt = (
        select(PlantSpec.common_name)
        .join(Plant, Plant.plant_spec_id == PlantSpec.id)
        .join(Garden, Plant.garden_id == Garden.id)
        .where(Garden.user_id == user_id, Plant.is_active.is_(True))
    )
    result = await session.execute(stmt)
    found_names = [row[0].lower() for row in result.all()]

    matched = []
    missing = []
    for expected in expected_plants:
        if any(expected.lower() in name for name in found_names):
            matched.append(expected)
        else:
            missing.append(expected)

    passed = len(missing) == 0
    return passed, matched


def check_banned_words(
    transcript: list[dict], banned_words: list[str]
) -> tuple[bool, list[str]]:
    """Check that no Sage response contains banned words/phrases.

    Single words match on word boundaries (so 'mate' won't match 'climate').
    Multi-word phrases match as substrings.

    Returns (passed, list_of_violations).
    """
    violations = []
    for entry in transcript:
        if entry["role"] != "sage":
            continue
        content_lower = entry["content"].lower()
        for word in banned_words:
            term = word.lower()
            if " " in term:
                hit = term in content_lower
            else:
                hit = re.search(rf"\b{re.escape(term)}\b", content_lower) is not None
            if hit:
                violations.append(
                    f"Turn {entry.get('turn', '?')}: found '{word}'"
                )
    return len(violations) == 0, violations


def check_no_empty_responses(transcript: list[dict]) -> tuple[bool, list[int]]:
    """Check that no Sage response is empty.

    Returns (passed, list_of_turn_numbers_with_empty_responses).
    """
    empty_turns = []
    for entry in transcript:
        if entry["role"] != "sage":
            continue
        if not entry["content"] or not entry["content"].strip():
            empty_turns.append(entry.get("turn", 0))
    return len(empty_turns) == 0, empty_turns


def check_response_length(
    transcript: list[dict], max_length: int
) -> tuple[bool, list[int]]:
    """Check that Sage responses don't exceed max_length characters.

    Returns (passed, list_of_turn_numbers_that_exceeded).
    """
    exceeded = []
    for entry in transcript:
        if entry["role"] != "sage":
            continue
        if len(entry["content"]) > max_length:
            exceeded.append(entry.get("turn", 0))
    return len(exceeded) == 0, exceeded


async def run_rule_checks(
    user: User,
    user_id,
    session: AsyncSession,
    transcript: list[dict],
    persona: Persona,
) -> dict:
    """Run all rule checks and return a results dict."""
    results = {}

    # 1. Onboarding complete
    results["onboarding_complete"] = await check_onboarding_complete(user)

    # 2. Plants created (skip if no expected plants, e.g. guardrails persona)
    if persona.expected_plants:
        passed, matched = await check_plants_created(
            user_id, session, persona.expected_plants
        )
        results["plants_created"] = passed
        results["plants_matched"] = matched
    else:
        results["plants_created"] = True
        results["plants_matched"] = []

    # 3. Banned words
    passed, violations = check_banned_words(transcript, persona.banned_words)
    results["no_banned_words"] = passed
    if violations:
        results["banned_word_violations"] = violations

    # 4. No empty responses
    passed, empty_turns = check_no_empty_responses(transcript)
    results["no_empty_responses"] = passed
    if empty_turns:
        results["empty_response_turns"] = empty_turns

    # 5. Response length
    passed, exceeded = check_response_length(transcript, persona.max_response_length)
    results["response_length_ok"] = passed
    if exceeded:
        results["length_exceeded_turns"] = exceeded

    return results


async def judge_conversation(
    transcript: list[dict],
    persona: Persona,
    client: anthropic.AsyncAnthropic,
) -> dict:
    """Use Claude as a judge to evaluate the full conversation.

    Returns a dict with scores (1-5) for each criterion plus an issues list.
    """
    # Format transcript for the judge
    formatted_lines = []
    for entry in transcript:
        role_label = "USER" if entry["role"] == "user" else "SAGE"
        formatted_lines.append(f"[{role_label}] {entry['content']}")
    formatted_transcript = "\n\n".join(formatted_lines)

    persona_description = (
        f"{persona.name}, age {persona.age}, postcode area {persona.postcode}. "
        f"{persona.persona_prompt}"
    )

    extra_criteria = ""
    if persona.judge_criteria:
        extra_criteria = f"\nAdditional criteria specific to this persona:\n{persona.judge_criteria}\n"

    judge_prompt = f"""You are evaluating a conversation between a gardening AI coach called Sage and a simulated user.

The user's profile: {persona_description}

Score each of Sage's responses on these criteria (1-5 each):
1. COACHING_STYLE: Did Sage tell beginners what to do, or ask questions they can't answer? For experts, did it engage as a peer?
2. TONE: Was it warm, encouraging, like a knowledgeable friend (not corporate, not zany)?
3. SPECIFICITY: Were recommendations specific (product names, prices, shops, varieties)?
4. FLOW: Did each response naturally lead to a next action?
5. CONCISENESS: Was it WhatsApp-style (2-4 sentences, no markdown, no bullet points)?
{extra_criteria}
Here is the full conversation transcript:

{formatted_transcript}

Respond with JSON only, no other text:
{{"coaching_style": N, "tone": N, "specificity": N, "flow": N, "conciseness": N, "overall": N, "issues": ["list of specific problems found"]}}"""

    try:
        response = await client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": judge_prompt}],
        )

        text = response.content[0].text.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in text:
            # Find content between first ``` and last ```
            start = text.index("```")
            end = text.rindex("```")
            inner = text[start + 3 : end]
            # Remove optional json language tag
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()

        scores = json.loads(text)
        return scores

    except Exception as e:
        logger.exception("Judge evaluation failed")
        return {"error": str(e)}
