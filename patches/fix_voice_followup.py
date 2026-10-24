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


# Global activation edge, reliable wake-to-command handoff, conversational TTS and local history.
vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
s = vm.read_text()
if "waitingForWakeGreeting" not in s:
    s = s.replace("    private var voiceManager: VoiceManager? = null\n", "    private var voiceManager: VoiceManager? = null\n    private var waitingForWakeGreeting = false\n    private var waitingForCommandReply = false\n", 1)
    s = s.replace("""        voiceManager?.onSpeechErrorCallback = { errorMsg ->
            addSystemLog("VOICE_EVENT: $errorMsg")
        }
""", """        voiceManager?.onSpeechErrorCallback = { errorMsg ->
            addSystemLog("VOICE_EVENT: $errorMsg")
        }
        voiceManager?.onSpeechCompletedCallback = {
            when {
                waitingForWakeGreeting -> {
                    waitingForWakeGreeting = false
                    voiceManager?.retryListeningOnTimeout = true
                    startListening()
                }
                waitingForCommandReply -> {
                    waitingForCommandReply = false
                    JarvisOverlayService.hide(context)
                    if (_isBackgroundListeningEnabled.value) {
                        viewModelScope.launch {
                            delay(900)
                            JarvisBackgroundService.resumeListening(context)
                        }
                    }
                }
            }
        }
""", 1)
    s = s.replace("""        voiceManager = VoiceManager(context) { recognizedText ->
            processUserCommand(recognizedText, isVoice = true)
        }
""", """        voiceManager = VoiceManager(context) { recognizedText ->
            voiceManager?.retryListeningOnTimeout = false
            processUserCommand(recognizedText, isVoice = true)
        }
""", 1)
    old = """        viewModelScope.launch {
            // Let the spoken wake acknowledgement finish before opening the command mic.
            delay(3500)
            startListening()
        }
"""
    new = """        waitingForWakeGreeting = true
        JarvisOverlayService.show(context)
        // Speak first; VoiceManager opens the command microphone only after TTS finishes.
        voiceManager?.speak(greeting, "JARVIS_WAKE_ACK")
"""
    if old not in s: raise Error("Could not find wake greeting delay in ViewModel")
    s = s.replace(old, new, 1)
    old = """            // Speak reply in natural Hindi, then restore the wake-word listener.
            speak(result.spokenResponse)
            if (isVoice && _isBackgroundListeningEnabled.value) {
                viewModelScope.launch {
                    // Give speech synthesis time to finish before handing the mic back to wake-word mode.
                    delay(8000)
                    JarvisBackgroundService.resumeListening(context)
                }
            }
"""
    new = """            // Return to wake-word standby only after the spoken completion message ends.
            if (isVoice) waitingForCommandReply = true
            speak(result.spokenResponse)
            if (isVoice && !_voiceAutoSpeakEnabled.value) {
                waitingForCommandReply = false
                JarvisOverlayService.hide(context)
                if (_isBackgroundListeningEnabled.value) JarvisBackgroundService.resumeListening(context)
            }
"""
    if old not in s: raise Error("Could not find command reply timer in ViewModel")
    s = s.replace(old, new, 1)
    # Persist up to 60 recent conversation messages across app restarts.
    marker = "    private fun executeResolvedAction(action: JarvisAction) {"
    persist = """    private fun persistConversation(messages: List<ChatMessage>) {
        try {
            val array = org.json.JSONArray()
            messages.takeLast(60).forEach { m ->
                array.put(org.json.JSONObject().apply {
                    put("text", m.text); put("isJarvis", m.isJarvis); put("timestamp", m.timestamp)
                    put("actionSummary", m.actionSummary ?: ""); put("isVoice", m.isVoice)
                })
            }
            context.getSharedPreferences("jarvis_local_memory", android.content.Context.MODE_PRIVATE)
                .edit().putString("conversation", array.toString()).apply()
        } catch (_: Exception) { }
    }

    private fun loadConversation(): List<ChatMessage> = try {
        val raw = context.getSharedPreferences("jarvis_local_memory", android.content.Context.MODE_PRIVATE)
            .getString("conversation", null) ?: return emptyList()
        val a = org.json.JSONArray(raw)
        (0 until a.length()).map { i ->
            val m = a.getJSONObject(i)
            ChatMessage(text = m.optString("text"), isJarvis = m.optBoolean("isJarvis"),
                timestamp = m.optLong("timestamp", System.currentTimeMillis()),
                actionSummary = m.optString("actionSummary").takeIf { it.isNotBlank() },
                isVoice = m.optBoolean("isVoice"))
        }
    } catch (_: Exception) { emptyList() }

"""
    s = s.replace(marker, persist + marker, 1)
    old = """        _messages.value = listOf(
            ChatMessage(
                text = "Namaste Sir! Main JARVIS hoon. Pure phone ka control lene ke liye taiyar. Aap mujhse voice ya chat mein kuch bhi pooch sakte hain!",
                isJarvis = true
            )
        )
"""
    new = """        _messages.value = loadConversation().ifEmpty {
            listOf(ChatMessage(
                text = "Namaste Sir! Main JARVIS hoon. Aap mujhse voice ya chat mein baat kar sakte hain.",
                isJarvis = true
            ))
        }
        viewModelScope.launch { _messages.collect { persistConversation(it) } }
"""
    if old not in s: raise Error("Could not find initial welcome message")
    s = s.replace(old, new, 1)
    vm.write_text(s)

voice = root / "app/src/main/java/com/example/util/VoiceManager.kt"
s = voice.read_text()
if "onSpeechCompletedCallback" not in s:
    s = s.replace("    var onSpeechErrorCallback: ((String) -> Unit)? = null\n", "    var onSpeechErrorCallback: ((String) -> Unit)? = null\n    var onSpeechCompletedCallback: (() -> Unit)? = null\n    var retryListeningOnTimeout: Boolean = false\n", 1)
    s = s.replace("                    engine.setPitch(0.92f)\n                    engine.setSpeechRate(1.0f)\n", """                    engine.setPitch(1.0f)
                    engine.setSpeechRate(0.94f)
                    try {
                        val hiVoice = engine.voices?.firstOrNull {
                            it.locale.language == "hi" && it.quality >= android.speech.tts.Voice.QUALITY_HIGH
                        }
                        if (hiVoice != null) engine.voice = hiVoice
                    } catch (_: Exception) { }
""", 1)
    s = s.replace("""            override fun onDone(utteranceId: String?) {
                _isSpeaking.value = false
            }
""", """            override fun onDone(utteranceId: String?) {
                _isSpeaking.value = false
                mainHandler.post { onSpeechCompletedCallback?.invoke() }
            }
""", 1)
    s = s.replace("""        onSpeechErrorCallback?.invoke(errorMessage)
    }
""", """        onSpeechErrorCallback?.invoke(errorMessage)
        if (retryListeningOnTimeout &&
            (error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT)) {
            mainHandler.postDelayed({
                if (retryListeningOnTimeout && !_isListening.value && !_isSpeaking.value) startListening()
            }, 700)
        }
    }
""", 1)
    s = s.replace("""        if (!text.isNullOrBlank()) {
            onVoiceResult(text)
        }
""", """        if (!text.isNullOrBlank()) {
            retryListeningOnTimeout = false
            onVoiceResult(text)
        }
""", 1)
    voice.write_text(s)

service = root / "app/src/main/java/com/example/service/JarvisBackgroundService.kt"
s = service.read_text()
s = s.replace("""        val wakeReply = "Haan sir, main active hoon! Boliye, kya kaam hai?"
        speakDirect(wakeReply)

        // Bring Jarvis into active foreground
""", """        // ViewModel speaks the acknowledgement and starts command capture after speech ends.
        JarvisOverlayService.show(this)

        // Bring Jarvis into active foreground
""", 1)
service.write_text(s)

manifest = root / "app/src/main/AndroidManifest.xml"
s = manifest.read_text()
if "android.permission.SYSTEM_ALERT_WINDOW" not in s:
    s = s.replace('    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n',
                  '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />\n', 1)
if ".service.JarvisOverlayService" not in s:
    s = s.replace("""        <service
            android:name=".service.JarvisBackgroundService"
            android:exported="false"
            android:foregroundServiceType="microphone" />
""", """        <service
            android:name=".service.JarvisBackgroundService"
            android:exported="false"
            android:foregroundServiceType="microphone" />
        <service
            android:name=".service.JarvisOverlayService"
            android:exported="false" />
""", 1)
manifest.write_text(s)

overlay = root / "app/src/main/java/com/example/service/JarvisOverlayService.kt"
if not overlay.exists():
    overlay.write_text('''package com.example.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.RectF
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowManager

class JarvisOverlayService : Service() {
    private var wm: WindowManager? = null
    private var edge: View? = null
    private val handler = Handler(Looper.getMainLooper())
    private val timeout = Runnable { stopSelf() }

    override fun onCreate() {
        super.onCreate()
        if (Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(this)) { stopSelf(); return }
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        edge = EdgeView(this)
        val type = if (Build.VERSION.SDK_INT >= 26) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                   else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE
        val p = WindowManager.LayoutParams(WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT, type,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT).apply { gravity = Gravity.TOP or Gravity.START }
        try { wm?.addView(edge, p) } catch (_: Exception) { stopSelf() }
        handler.postDelayed(timeout, 45000)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_HIDE) stopSelf()
        else { handler.removeCallbacks(timeout); handler.postDelayed(timeout, 45000) }
        return START_NOT_STICKY
    }
    override fun onDestroy() {
        handler.removeCallbacks(timeout)
        try { edge?.let { wm?.removeView(it) } } catch (_: Exception) { }
        edge = null
        super.onDestroy()
    }
    override fun onBind(intent: Intent?): IBinder? = null

    private class EdgeView(c: Context) : View(c) {
        private val p = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = android.graphics.Color.rgb(0, 255, 100); style = Paint.Style.STROKE; strokeWidth = 8f
            setShadowLayer(16f, 0f, 0f, android.graphics.Color.rgb(0, 255, 100))
        }
        override fun onDraw(c: Canvas) {
            super.onDraw(c)
            val i = p.strokeWidth / 2f + 2f
            c.drawRoundRect(RectF(i, i, width - i, height - i), 20f, 20f, p)
        }
    }
    companion object {
        const val ACTION_HIDE = "com.example.service.JARVIS_OVERLAY_HIDE"
        fun show(c: Context) {
            if (Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(c)) return
            try { c.startService(Intent(c, JarvisOverlayService::class.java)) } catch (_: Exception) { }
        }
        fun hide(c: Context) { try { c.stopService(Intent(c, JarvisOverlayService::class.java)) } catch (_: Exception) { } }
        fun overlaySettingsIntent(c: Context) = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${c.packageName}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
}
''')

main = root / "app/src/main/java/com/example/MainActivity.kt"
s = main.read_text()
if "requestOverlayPermissionOnce" not in s:
    s = s.replace("        requestPermissionsIfNeeded()\n        enableEdgeToEdge()\n",
                  "        requestPermissionsIfNeeded()\n        requestOverlayPermissionOnce()\n        enableEdgeToEdge()\n", 1)
    anchor = "    private fun requestPermissionsIfNeeded() {"
    method = """    private fun requestOverlayPermissionOnce() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !android.provider.Settings.canDrawOverlays(this)) {
            val prefs = getSharedPreferences("jarvis_local_memory", MODE_PRIVATE)
            if (!prefs.getBoolean("overlay_permission_prompted", false)) {
                prefs.edit().putBoolean("overlay_permission_prompted", true).apply()
                android.os.Handler(mainLooper).postDelayed({
                    if (!isFinishing && !android.provider.Settings.canDrawOverlays(this)) {
                        startActivity(com.example.service.JarvisOverlayService.overlaySettingsIntent(this))
                    }
                }, 1800)
            }
        }
    }

"""
    if anchor not in s: raise Error("MainActivity permission anchor missing")
    s = s.replace(anchor, method + anchor, 1)
main.write_text(s)
print("Applied global green edge overlay, speech-sequenced command listening, conversational TTS tuning and saved recent chat history.")


# Kotlin compatibility touch-ups for the generated additions.
vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
s = vm.read_text()
if "import com.example.service.JarvisOverlayService" not in s:
    s = s.replace("import com.example.service.JarvisBackgroundService\n",
                  "import com.example.service.JarvisBackgroundService\nimport com.example.service.JarvisOverlayService\n", 1)
s = s.replace("""    private fun loadConversation(): List<ChatMessage> = try {
        val raw = context.getSharedPreferences("jarvis_local_memory", android.content.Context.MODE_PRIVATE)
            .getString("conversation", null) ?: return emptyList()
        val a = org.json.JSONArray(raw)
        (0 until a.length()).map { i ->
            val m = a.getJSONObject(i)
            ChatMessage(text = m.optString("text"), isJarvis = m.optBoolean("isJarvis"),
                timestamp = m.optLong("timestamp", System.currentTimeMillis()),
                actionSummary = m.optString("actionSummary").takeIf { it.isNotBlank() },
                isVoice = m.optBoolean("isVoice"))
        }
    } catch (_: Exception) { emptyList() }
""", """    private fun loadConversation(): List<ChatMessage> {
        return try {
            val raw = context.getSharedPreferences("jarvis_local_memory", android.content.Context.MODE_PRIVATE)
                .getString("conversation", null) ?: return emptyList()
            val a = org.json.JSONArray(raw)
            (0 until a.length()).map { i ->
                val m = a.getJSONObject(i)
                ChatMessage(text = m.optString("text"), isJarvis = m.optBoolean("isJarvis"),
                    timestamp = m.optLong("timestamp", System.currentTimeMillis()),
                    actionSummary = m.optString("actionSummary").takeIf { it.isNotBlank() },
                    isVoice = m.optBoolean("isVoice"))
            }
        } catch (_: Exception) { emptyList() }
    }
""")
vm.write_text(s)
