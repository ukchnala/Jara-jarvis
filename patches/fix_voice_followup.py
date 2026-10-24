from pathlib import Path
import sys

root = Path(sys.argv[1])

# Give the wake acknowledgement time to finish before opening the command microphone.
vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
v = vm.read_text()
v = v.replace("delay(1800)", "delay(3500)")
v = v.replace("delay(5000)", "delay(8000)")
vm.write_text(v)

# Allow a natural pause within a longer spoken command before speech recognition finalizes it.
voice = root / "app/src/main/java/com/example/util/VoiceManager.kt"
s = voice.read_text()
s = s.replace(
    '                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)\n',
    '                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)\n'
    '                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 1200L)\n'
    '                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 2200L)\n'
    '                    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1400L)\n'
    '                    putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, false)\n'
)
voice.write_text(s)

# Green frame on all four screen edges while listening or speaking.
ui = root / "app/src/main/java/com/example/ui/screens/JarvisMainContainer.kt"
s = ui.read_text()
s = s.replace(
    '        modifier = Modifier\n            .fillMaxSize()\n            .background(JarvisDeepDark),\n',
    '        modifier = Modifier\n'
    '            .fillMaxSize()\n'
    '            .background(JarvisDeepDark)\n'
    '            .border(\n'
    '                width = if (isListening || isSpeaking) 4.dp else 0.dp,\n'
    '                color = if (isListening || isSpeaking) JarvisNeonGreen else Color.Transparent\n'
    '            ),\n',
    1
)
ui.write_text(s)

# Do not claim a complex task was completed when no general AI planner is configured.
intel = root / "app/src/main/java/com/example/util/JarvisIntelligence.kt"
s = intel.read_text()
start = s.find("        // Fallback intelligent Hindi response")
end = s.find("\n\n        return InterpretationResult(", start)
if start >= 0 and end > start:
    s = s[:start] + '''        // This build has local rule-based commands, not a connected general-purpose AI planner.
        val fallback = if (phoneControlEnabled) {
            "Sir, maine aapki baat suni: \\"$input\\". Is build mein abhi general AI task planner connected nahi hai, isliye main app design ya bade multi-step kaam ko khud se complete karne ka daawa nahi karunga. Main supported phone commands execute kar sakta hoon."
        } else {
            "Sir, maine aapki baat suni: \\"$input\\". Bade multi-step kaam ke liye general AI task planner connected hona zaroori hai. Filhaal main supported phone commands chala sakta hoon."
        }
''' + s[end:]
intel.write_text(s)

print("Applied command-listening timing, green activation frame, and truthful unsupported-task response.")
