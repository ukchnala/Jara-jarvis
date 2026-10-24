from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
client = root / "app/src/main/java/com/example/util/JarvisAiBackend.kt"
s = client.read_text()

# SharedPreferences returns a previously saved empty string instead of the default
# argument. Older builds saved blank values, so explicitly fall back when blank.
s = s.replace(
    '.getString(URL_KEY, "https://jarvis-ai-backend-8mzs.onrender.com")?.trim().orEmpty()',
    '.getString(URL_KEY, null)?.trim().orEmpty().ifBlank { "https://jarvis-ai-backend-8mzs.onrender.com" }'
)

# Reuse the token already configured by the existing patch without duplicating it
# in this new patch file. A saved blank token must not override that fallback.
match = re.search(r'\.getString\(TOKEN_KEY, "([^"]+)"\)\?\.trim\(\)\.orEmpty\(\)', s)
if match:
    fallback = match.group(1)
    s = s.replace(
        match.group(0),
        '.getString(TOKEN_KEY, null)?.trim().orEmpty().ifBlank { "' + fallback + '" }',
        1
    )

client.write_text(s)
print("JARVIS settings fallback patch applied.")
