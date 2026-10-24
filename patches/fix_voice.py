from pathlib import Path
import sys
root = Path(sys.argv[1])

main = root / "app/src/main/java/com/example/MainActivity.kt"
main.write_text("""package com.example

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import com.example.service.JarvisBackgroundService
import com.example.ui.screens.JarvisMainContainer
import com.example.ui.theme.MyApplicationTheme
import com.example.viewmodel.JarvisViewModel

class MainActivity : ComponentActivity() {
    private val jarvisViewModel: JarvisViewModel by viewModels()

    private val audioPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) requestNotificationPermissionIfNeeded()
        else Toast.makeText(this, "Jarvis ko sunne ke liye Microphone permission zaroori hai.", Toast.LENGTH_LONG).show()
    }
    private val notificationPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestPermissionsIfNeeded()
        enableEdgeToEdge()
        handleWakeIntent(intent)
        setContent { MyApplicationTheme { JarvisMainContainer(viewModel = jarvisViewModel) } }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleWakeIntent(intent)
    }

    override fun onStop() {
        super.onStop()
        if (!isChangingConfigurations && JarvisBackgroundService.isRunning.value) JarvisBackgroundService.resumeListening(this)
    }

    private fun requestPermissionsIfNeeded() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            audioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        } else requestNotificationPermissionIfNeeded()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private fun handleWakeIntent(intent: Intent?) {
        if (intent?.getBooleanExtra("EXTRA_WAKE_TRIGGER", false) == true) {
            jarvisViewModel.onWakeWordActivated()
            intent.removeExtra("EXTRA_WAKE_TRIGGER")
        }
    }
}
""")

svc = root / "app/src/main/java/com/example/service/JarvisBackgroundService.kt"
s = svc.read_text()
s = s.replace("import android.app.Service\n", "import android.app.Service\nimport android.Manifest\nimport android.content.pm.PackageManager\n")
s = s.replace("import androidx.core.app.NotificationCompat\n", "import androidx.core.app.NotificationCompat\nimport androidx.core.content.ContextCompat\n")
s = s.replace("    private var isAudioThreadRunning = false\n    private var lastWakeTriggerTime = 0L\n", "    private var isAudioThreadRunning = false\n    private var isRecognitionActive = false\n    private var isRecognitionPaused = false\n    private var lastWakeTriggerTime = 0L\n")
s = s.replace("""        super.onCreate()
        _isRunning.value = true
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("JARVIS Background Listening Active", "Wake Word: 'Hey Jarvis' listening..."))

        initTts()
        initSpeechRecognizer()
        startAudioActivityMonitoring()
""", """        super.onCreate()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            stopSelf()
            return
        }
        _isRunning.value = true
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("JARVIS Background Listening Active", "Wake word 'Jarvis' listener is running"))
        initTts()
        initSpeechRecognizer()
        // Do not run AudioRecord beside SpeechRecognizer; both compete for the microphone.
""")
s = s.replace("""                        override fun onError(error: Int) {
                            scheduleNextRecognition()
                        }
                        override fun onResults(results: Bundle?) {
                            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                            val text = matches?.firstOrNull()?.trim() ?: ""
                            if (text.isNotBlank()) {
                                handleRecognizedText(text)
                            }
                            scheduleNextRecognition()
                        }
""", """                        override fun onError(error: Int) {
                            isRecognitionActive = false
                            scheduleNextRecognition()
                        }
                        override fun onResults(results: Bundle?) {
                            isRecognitionActive = false
                            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                            val text = matches?.firstOrNull()?.trim() ?: ""
                            if (text.isNotBlank()) handleRecognizedText(text)
                            scheduleNextRecognition()
                        }
""")
s = s.replace("""                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "hi-IN")
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                }
                speechRecognizer?.startListening(intent)
""", """                if (!_isRunning.value || isRecognitionPaused || isRecognitionActive || speechRecognizer == null) return@post
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-IN")
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "en-IN")
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, false)
                }
                speechRecognizer?.startListening(intent)
                isRecognitionActive = true
""")
s = s.replace("            if (_isRunning.value) {\n                startRecognitionCycle()\n            }", "            if (_isRunning.value && !isRecognitionPaused) {\n                startRecognitionCycle()\n            }")
s = s.replace('''            "jarvis",
            "jarvish",
''', '''            "jarvis",
            "jarvish",
            "जार्विस",
            "जार्विश",
            "जारविस",
''')
s = s.replace("""    fun triggerWakeResponse() {
        val now = System.currentTimeMillis()
        if (now - lastWakeTriggerTime < 2500) return // Debounce
        lastWakeTriggerTime = now

        DeviceController.vibrate(this, 90)
""", """    fun triggerWakeResponse() {
        val now = System.currentTimeMillis()
        if (now - lastWakeTriggerTime < 2500) return // Debounce
        lastWakeTriggerTime = now
        pauseRecognition()
        DeviceController.vibrate(this, 90)
""")
s = s.replace("""            ACTION_TRIGGER_WAKE -> {
                triggerWakeResponse()
            }
""", """            ACTION_TRIGGER_WAKE -> triggerWakeResponse()
            ACTION_PAUSE_LISTENER -> pauseRecognition()
            ACTION_RESUME_LISTENER -> {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                    isRecognitionPaused = false
                    if (speechRecognizer == null) initSpeechRecognizer() else startRecognitionCycle()
                }
            }
""")
marker = "    private fun isWakeWordMatch(query: String): Boolean {"
pause = """    private fun pauseRecognition() {
        isRecognitionPaused = true
        isRecognitionActive = false
        mainHandler.post {
            try {
                speechRecognizer?.cancel()
                speechRecognizer?.destroy()
            } catch (_: Exception) { }
            speechRecognizer = null
        }
    }

"""
s = s.replace(marker, pause + marker)
s = s.replace('''        const val ACTION_TRIGGER_WAKE = "com.example.service.TRIGGER_WAKE"
''', '''        const val ACTION_TRIGGER_WAKE = "com.example.service.TRIGGER_WAKE"
        const val ACTION_PAUSE_LISTENER = "com.example.service.PAUSE_LISTENER"
        const val ACTION_RESUME_LISTENER = "com.example.service.RESUME_LISTENER"
''')
s = s.replace("""        fun triggerWake(context: Context) {
            val intent = Intent(context, JarvisBackgroundService::class.java).apply {
                action = ACTION_TRIGGER_WAKE
            }
            context.startService(intent)
        }
""", """        fun triggerWake(context: Context) {
            val intent = Intent(context, JarvisBackgroundService::class.java).apply { action = ACTION_TRIGGER_WAKE }
            context.startService(intent)
        }

        fun pauseListening(context: Context) {
            val intent = Intent(context, JarvisBackgroundService::class.java).apply { action = ACTION_PAUSE_LISTENER }
            context.startService(intent)
        }

        fun resumeListening(context: Context) {
            val intent = Intent(context, JarvisBackgroundService::class.java).apply { action = ACTION_RESUME_LISTENER }
            context.startService(intent)
        }
""")
svc.write_text(s)

vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
v = vm.read_text()
needle = "    fun triggerWakeWordTest() {"
addition = """    fun onWakeWordActivated() {
        _activeTab.value = JarvisTab.VOICE_CHAT
        val greeting = "Haan sir, main active hoon! Boliye, kya kaam hai?"
        _messages.value = _messages.value + ChatMessage(text = greeting, isJarvis = true, actionSummary = "Wake word detected")
        addSystemLog("WAKE_WORD: Jarvis detected; voice chat activated")
        viewModelScope.launch {
            delay(2500)
            startListening()
        }
    }

"""
if needle not in v:
    raise SystemExit("Could not find ViewModel insertion point")
v = v.replace(needle, addition + needle, 1)
v = v.replace("""    fun startListening() {
        voiceManager?.startListening()
    }

    fun stopListening() {
        voiceManager?.stopListening()
    }
""", """    fun startListening() {
        if (_isBackgroundListeningEnabled.value) JarvisBackgroundService.pauseListening(context)
        voiceManager?.startListening()
    }

    fun stopListening() {
        voiceManager?.stopListening()
        if (_isBackgroundListeningEnabled.value) JarvisBackgroundService.resumeListening(context)
    }
""")
v = v.replace("""            // Speak reply in natural Hindi
            speak(result.spokenResponse)
""", """            // Speak reply in natural Hindi, then restore the wake-word listener.
            speak(result.spokenResponse)
            if (isVoice && _isBackgroundListeningEnabled.value) {
                viewModelScope.launch {
                    delay(5000)
                    JarvisBackgroundService.resumeListening(context)
                }
            }
""")
vm.write_text(v)
print("Applied Jarvis voice/wake-word fixes to extracted original project.")
