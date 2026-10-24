from pathlib import Path
import sys

root = Path(sys.argv[1])

planner = root / "app/src/main/java/com/example/util/JarvisTaskPlanner.kt"
planner.write_text(r'''package com.example.util

object JarvisTaskPlanner {
    private val separators = Regex(
        """\s*(?:,|;|\band then\b|\bafter that\b|\bthen\b|\baur phir\b|\buske baad\b|\bphir\b|\baur\b)\s*""",
        RegexOption.IGNORE_CASE
    )

    fun split(command: String): List<String> {
        val cleaned = command.trim().replace(Regex("\\s+"), " ")
        if (cleaned.isBlank()) return emptyList()
        val steps = separators.split(cleaned)
            .map { it.trim().trim('.', '!', '?') }
            .filter { it.length >= 2 }
        return if (steps.size <= 1) listOf(cleaned) else steps.take(5)
    }
}
''')

proactive = root / "app/src/main/java/com/example/service/JarvisProactiveManager.kt"
proactive.write_text(r'''package com.example.service

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.example.MainActivity
import com.example.R
import java.util.Calendar

object JarvisProactiveManager {
    const val PREFS = "jarvis_proactive"
    const val KEY_ENABLED = "enabled"
    private const val CHANNEL_ID = "jarvis_checkins"
    private const val NOTIFICATION_ID = 7314
    private const val REQUEST_CODE = 7315

    fun isEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(KEY_ENABLED, false)

    fun setEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_ENABLED, enabled).apply()
        if (enabled) schedule(context) else cancel(context)
    }

    fun schedule(context: Context) {
        if (!isEnabled(context)) return
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val intent = Intent(context, JarvisProactiveReceiver::class.java).setAction("com.example.JARVIS_CHECK_IN")
        val pending = PendingIntent.getBroadcast(context, REQUEST_CODE, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val next = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 19); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) add(Calendar.DAY_OF_YEAR, 1)
        }
        alarm.setInexactRepeating(AlarmManager.RTC_WAKEUP, next.timeInMillis, AlarmManager.INTERVAL_DAY, pending)
    }

    fun cancel(context: Context) {
        val alarm = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val intent = Intent(context, JarvisProactiveReceiver::class.java).setAction("com.example.JARVIS_CHECK_IN")
        val pending = PendingIntent.getBroadcast(context, REQUEST_CODE, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        alarm.cancel(pending); pending.cancel()
    }

    fun showCheckIn(context: Context) {
        if (!isEnabled(context)) return
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(NotificationChannel(CHANNEL_ID, "JARVIS check-ins", NotificationManager.IMPORTANCE_DEFAULT))
        }
        val open = Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val content = PendingIntent.getActivity(context, REQUEST_CODE, open,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        val message = when {
            hour in 16..21 -> "Khana khaya? Agar din busy tha to thoda break le lena."
            hour in 11..15 -> "Paani piya hai? Thoda sa break lena bhi zaroori hai."
            else -> "Sab theek chal raha hai? Agar kisi kaam mein help chahiye, JARVIS ready hai."
        }
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher).setContentTitle("JARVIS").setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message)).setContentIntent(content)
            .setAutoCancel(true).build()
        try { manager.notify(NOTIFICATION_ID, notification) } catch (_: SecurityException) { }
    }
}

class JarvisProactiveReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        when (intent?.action) {
            Intent.ACTION_BOOT_COMPLETED -> JarvisProactiveManager.schedule(context)
            "com.example.JARVIS_CHECK_IN" -> JarvisProactiveManager.showCheckIn(context)
        }
    }
}
''')

manifest = root / "app/src/main/AndroidManifest.xml"
m = manifest.read_text()
if 'android.permission.RECEIVE_BOOT_COMPLETED' not in m:
    m = m.replace('    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />',
                  '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />')
if 'JarvisProactiveReceiver' not in m:
    m = m.replace('        <service\\n            android:name=".service.JarvisOverlayService"',
                  '        <receiver android:name=".service.JarvisProactiveReceiver" android:enabled="true" android:exported="true">\\n'
                  '            <intent-filter>\\n'
                  '                <action android:name="com.example.JARVIS_CHECK_IN" />\\n'
                  '                <action android:name="android.intent.action.BOOT_COMPLETED" />\\n'
                  '            </intent-filter>\\n'
                  '        </receiver>\\n'
                  '        <service\\n            android:name=".service.JarvisOverlayService')
manifest.write_text(m)

vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
v = vm.read_text()
if 'import com.example.service.JarvisProactiveManager' not in v:
    v = v.replace('import com.example.service.JarvisBackgroundService\n',
                  'import com.example.service.JarvisBackgroundService\nimport com.example.service.JarvisProactiveManager\nimport com.example.util.JarvisTaskPlanner\n')
anchor = '''        viewModelScope.launch {
            delay(100)
            val result = JarvisIntelligence.interpret(input, context, _phoneControlEnabled.value)
'''
replacement = '''        viewModelScope.launch {
            delay(100)
            val lower = input.lowercase(Locale.ROOT)
            val proactiveOn = listOf("proactive mode on", "proactive baatein on", "khud se baat karo", "khud se baat on", "check in on").any { lower.contains(it) }
            val proactiveOff = listOf("proactive mode off", "proactive baatein off", "khud se baat band", "check in off").any { lower.contains(it) }
            if (proactiveOn || proactiveOff) {
                JarvisProactiveManager.setEnabled(context, proactiveOn)
                val reply = if (proactiveOn) {
                    "Theek hai sir. Roz shaam ko ek chhota JARVIS check-in notification bhejunga. Band karne ke liye 'proactive mode off' bol dena."
                } else {
                    "Theek hai sir. Proactive check-ins band kar diye hain."
                }
                addSystemLog("PROACTIVE_CHECKINS: " + if (proactiveOn) "ENABLED" else "DISABLED")
                _messages.value = _messages.value + ChatMessage(text = reply, isJarvis = true, actionSummary = "Proactive check-ins")
                speak(reply)
                return@launch
            }

            val plannedSteps = JarvisTaskPlanner.split(input)
            if (plannedSteps.size > 1) {
                val completed = mutableListOf<String>()
                val unsupported = mutableListOf<String>()
                for ((index, step) in plannedSteps.withIndex()) {
                    val result = JarvisIntelligence.interpret(step, context, _phoneControlEnabled.value)
                    if (result.action is JarvisAction.Conversational) {
                        unsupported.add(step)
                        addSystemLog("PLAN_STEP_SKIPPED: No executable phone action matched '$step'")
                    } else {
                        addSystemLog("PLAN_STEP ${index + 1}/${plannedSteps.size}: ${result.actionLog}")
                        executeResolvedAction(result.action)
                        completed.add(step)
                    }
                    delay(350)
                }
                val reply = when {
                    unsupported.isEmpty() -> "Sir, ${completed.size} steps execute kar diye: " + completed.joinToString("; ") + "."
                    completed.isEmpty() -> "Sir, main in steps ko abhi execute nahi kar saka: " + unsupported.joinToString("; ") + ". Inke liye supported phone action ya AI service chahiye."
                    else -> "${completed.size} steps execute hue. Ye steps nahi ho sake: " + unsupported.joinToString("; ") + "."
                }
                _messages.value = _messages.value + ChatMessage(
                    text = reply, isJarvis = true,
                    actionSummary = "Task plan: ${completed.size} completed, ${unsupported.size} unsupported",
                    isVoice = isVoice
                )
                speak(reply)
                return@launch
            }

            val result = JarvisIntelligence.interpret(input, context, _phoneControlEnabled.value)
'''
if anchor in v:
    v = v.replace(anchor, replacement, 1)
else:
    raise RuntimeError("Could not locate processUserCommand planner insertion anchor")
vm.write_text(v)

main = root / "app/src/main/java/com/example/MainActivity.kt"
a = main.read_text()
if 'POST_NOTIFICATIONS' not in a:
    a = a.replace('import android.os.Bundle\n', 'import android.os.Bundle\nimport android.Manifest\nimport android.content.pm.PackageManager\nimport android.os.Build\nimport androidx.core.app.ActivityCompat\nimport androidx.core.content.ContextCompat\n')
    a = a.replace('        super.onCreate(savedInstanceState)\n', '''        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 7316)
        }
''', 1)
main.write_text(a)

print("Added multi-step supported-action planner and opt-in daily proactive check-ins.")
