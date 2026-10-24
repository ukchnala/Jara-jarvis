from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
s = vm.read_text()

# The existing Kotlin regex was emitted with a single escaped backslash, which
# Kotlin interprets as a backspace escape rather than a regex word boundary.
# Avoid brittle Hindi/English speech-to-text detection entirely: let the backend
# planner handle every command when configured, before the local planner can
# respond with the stale "connect AI/task planner" prompt.
pattern = r'val aiMultiStep\s*=\s*Regex\([^\n]+'
s, count = re.subn(pattern, 'val aiMultiStep = true', s, count=1)
if count != 1:
    raise RuntimeError("Could not locate AI multi-step routing line; refusing to build without the fix.")

# Keep the backend as the first handler for all commands, not only conversational
# answers or commands containing particular connector words.
vm.write_text(s)
print("JARVIS command routing fixed: configured AI backend gets first chance for every command.")
