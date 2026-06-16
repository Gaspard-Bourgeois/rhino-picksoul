# -*- coding: utf-8 -*-
import scriptcontext as sc
import Rhino

EXCLUSION_LIST = [
    "_RunPythonScript",
]

def _get_command_history():
    text = Rhino.RhinoApp.CommandHistoryWindowText
    if not text:
        return []
    lines = text.split("\n")
    commands = []
    for line in lines:
        line = line.strip()
        for prefix in ("Commande: ", "Command: "):
            if line.startswith(prefix):
                commands.append(line[len(prefix):].strip())
                break
    return commands

def _last_non_excluded():
    history = _get_command_history()
    for cmd in reversed(history[:-1]):
        if not any(cmd == ex for ex in EXCLUSION_LIST):
            return cmd
    return None

def _is_repeated_excluded_call():
    history = _get_command_history()
    if len(history) < 2:
        return False
    last     = history[-1]
    previous = history[-2]
    return any(last == ex for ex in EXCLUSION_LIST) and any(previous == ex for ex in EXCLUSION_LIST)

def run(func):
    if _is_repeated_excluded_call():
        fallback = _last_non_excluded()
        if fallback:
            Rhino.RhinoApp.RunScript(fallback, False)
        return

    undo_was_enabled = sc.doc.UndoRecordingEnabled
    sc.doc.UndoRecordingEnabled = False
    try:
        func()
    finally:
        sc.doc.UndoRecordingEnabled = undo_was_enabled