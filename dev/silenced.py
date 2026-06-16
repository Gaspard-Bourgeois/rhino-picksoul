# -*- coding: utf-8 -*-
import scriptcontext as sc
import Rhino

# Liste des noms de commandes exclues (tels qu'ils apparaissent dans l'historique)
EXCLUSION_LIST = [
    "_RunPythonScript",
]

def _get_command_history():
    """Retourne toutes les commandes depuis l'historique texte."""
    text = Rhino.RhinoApp.CommandHistoryWindowText
    if not text:
        return []
    lines = text.split("\n")
    commands = []
    for line in lines:
        line = line.strip()
        if line.startswith("Commande: ") or line.startswith("Command: "):
            for prefix in ("Commande: ", "Command: "):
                if line.startswith(prefix):
                    commands.append(line[len(prefix):].strip())
                    break
    return commands

def _last_non_excluded():
    """Retourne la dernière commande hors liste d'exclusion."""
    history = _get_command_history()
    # On parcourt à l'envers en ignorant la dernière (commande courante)
    for cmd in reversed(history[:-1]):
        excluded = False
        for ex in EXCLUSION_LIST:
            if cmd == ex:
                excluded = True
                break
        if not excluded:
            return cmd
    return None

def _current_command_is_excluded():
    """Retourne True si la dernière commande dans l'historique est exclue."""
    history = _get_command_history()
    if not history:
        return False
    last = history[-1]
    for ex in EXCLUSION_LIST:
        if last == ex:
            return True
    return False

def _is_repeated_excluded_call():
    """
    Retourne True si :
    - la commande courante est exclue
    - ET la commande précédente était aussi exclue (= rappel par Entrée)
    """
    history = _get_command_history()
    if len(history) < 2:
        return False
    last = history[-1]
    previous = history[-2]
    last_excluded = any(last == ex for ex in EXCLUSION_LIST)
    prev_excluded = any(previous == ex for ex in EXCLUSION_LIST)
    return last_excluded and prev_excluded

def run(func):
    """
    Décorateur IronPython 2.7.
    - Si rappel par Entrée d'une commande exclue : réexécute la dernière commande valide
    - Désactive Undo pendant l'exécution
    Usage :
        import silenced
        @silenced.run
        def main():
            ...
        main()
    """
    def wrapper(*args, **kwargs):
        if _is_repeated_excluded_call():
            fallback = _last_non_excluded()
            if fallback:
                Rhino.RhinoApp.RunScript(fallback, False)
            return

        undo_was_enabled = sc.doc.UndoRecordingEnabled
        sc.doc.UndoRecordingEnabled = False
        try:
            return func(*args, **kwargs)
        finally:
            sc.doc.UndoRecordingEnabled = undo_was_enabled

    return wrapper