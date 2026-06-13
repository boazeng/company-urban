"""Agent registry — maps an agent name to its channel-agnostic brain.

Two kinds of brain, both exposing chat(history) -> str:
  • bespoke  — lives with the agent (the ran model), loaded by file path
               (e.g. רונית → ronit_core.py). Has real tools/data.
  • exec     — generic role-driven brain (exec_brain.py) for management agents
               that don't have a bespoke core yet (CEO/CFO/COO).

Adding an agent = one line (bespoke path or an exec profile).
"""
import os
import importlib.util
import inspect

import exec_brain
import cmd_brain

VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")

BESPOKE = {
    "רונית": rf"{VAULT}/Agents/marketing - cmo/RONIT/ronit_core.py",
    "רן": rf"{VAULT}/Agents/מנכ״ל/רן/ran_core.py",  # העוזר האישי + מרכזן (Front Door)
    # future bespoke cores: "סמנכ״ל כספים": ".../cfo_core.py", ...
}

HUMAN = "בועז"  # the human owner; messages from this author map to role 'user'


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_loaded = {}


def _brain(agent):
    """Return a chat(history)->str callable for the agent, or None."""
    if agent in _loaded:
        return _loaded[agent]
    fn = None
    if agent in BESPOKE:
        fn = _load(BESPOKE[agent], f"brain_{len(_loaded)}").chat
    elif exec_brain.has_profile(agent):
        fn = exec_brain.make_chat(agent)
    elif cmd_brain.has_agent(agent):
        fn = cmd_brain.make_chat(agent)
    if fn is not None:
        _loaded[agent] = fn
    return fn


def known_agents():
    # bespoke first, then generic execs, then command-agents (deduped)
    names = list(BESPOKE.keys())
    for a in list(exec_brain.PROFILES) + list(cmd_brain.COMMANDS):
        if a not in names:
            names.append(a)
    return names


def history_for(messages, speaker):
    """Build an Anthropic-style history from room messages, from `speaker`'s POV:
    the speaker's own past lines are 'assistant', everyone else is 'user'.
    Non-human speakers are prefixed with their name so the agent knows who said what."""
    hist = []
    for m in messages:
        if m["author"] == speaker:
            hist.append({"role": "assistant", "content": m["text"]})
        else:
            prefix = "" if m["author"] == HUMAN else f"[{m['author']}] "
            hist.append({"role": "user", "content": prefix + m["text"]})
    # collapse consecutive same-role turns (Anthropic requires alternation)
    merged = []
    for h in hist:
        if merged and merged[-1]["role"] == h["role"]:
            merged[-1]["content"] += "\n\n" + h["content"]
        else:
            merged.append(dict(h))
    return merged


def agent_reply(agent, messages, room_id=None):
    """Run the agent's brain over the room history. Returns reply text or None.
    Brains that declare a `room_id` parameter (e.g. רן, for inviting others) get it."""
    brain = _brain(agent)
    if brain is None:
        return None
    hist = history_for(messages, agent)
    try:
        if "room_id" in inspect.signature(brain).parameters:
            return brain(hist, room_id=room_id)
    except (TypeError, ValueError):
        pass
    return brain(hist)
