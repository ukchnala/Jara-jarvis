from pathlib import Path

root = Path("work")

# The original APK patch only saved a backend URL and did not send the required
# JARVIS_CLIENT_TOKEN. Add a token field and send it as Bearer authorization.
client = root / "app/src/main/java/com/example/util/JarvisAiBackend.kt"
s = client.read_text()
s = s.replace('    private const val URL_KEY = "endpoint_url"\n',
              '    private const val URL_KEY = "endpoint_url"\n    private const val TOKEN_KEY = "client_token"\n')
s = s.replace('''    fun saveEndpoint(context: Context, value: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(URL_KEY, value.trim().trimEnd('/')).apply()
    }
    fun isConfigured(context: Context) = endpoint(context).startsWith("https://")''',
'''    fun clientToken(context: Context): String = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        .getString(TOKEN_KEY, "")?.trim().orEmpty()
    fun saveEndpoint(context: Context, value: String, token: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(URL_KEY, value.trim().trimEnd('/'))
            .putString(TOKEN_KEY, token.trim()).apply()
    }
    fun isConfigured(context: Context) = endpoint(context).startsWith("https://") && clientToken(context).length >= 24''')
s = s.replace('.post(payload.toString().toRequestBody(jsonType)).header("Accept", "application/json").build()',
              '.post(payload.toString().toRequestBody(jsonType)).header("Accept", "application/json")\n                    .header("Authorization", "Bearer " + clientToken(context)).build()')
# Normalize duplicate lines because earlier builds may already have applied part of this patch.
lines = s.splitlines()
seen = set()
s = "\n".join(line for line in lines if not (line.strip() == 'private const val TOKEN_KEY = "client_token"' and line.strip() in seen) and not (seen.add(line.strip()) and False)) + "\n"
if "TOKEN_KEY" not in s or 'header("Authorization"' not in s:
    raise RuntimeError("Failed to patch JarvisAiBackend.kt")
client.write_text(s)

vm = root / "app/src/main/java/com/example/viewmodel/JarvisViewModel.kt"
s = vm.read_text()
s = s.replace('''    fun saveAiBackendEndpoint(value: String) {
        JarvisAiBackend.saveEndpoint(context, value)''',
'''    fun saveAiBackendEndpoint(value: String, token: String) {
        JarvisAiBackend.saveEndpoint(context, value, token)''')
if "fun saveAiBackendEndpoint(value: String, token: String)" not in s:
    raise RuntimeError("Failed to patch ViewModel save function")
vm.write_text(s)

screen = root / "app/src/main/java/com/example/ui/screens/VoiceChatScreen.kt"
s = screen.read_text()
s = s.replace('    onSaveAiBackendEndpoint: (String) -> Unit', '    onSaveAiBackendEndpoint: (String, String) -> Unit')
s = s.replace('    var endpointDraft by remember(aiBackendEndpoint) { mutableStateOf(aiBackendEndpoint) }',
              '    var endpointDraft by remember(aiBackendEndpoint) { mutableStateOf(aiBackendEndpoint) }\n    var clientTokenDraft by remember { mutableStateOf("") }')
s = s.replace('''                    OutlinedTextField(value = endpointDraft, onValueChange = { endpointDraft = it },
                        label = { Text("https://your-backend.example.com") }, singleLine = true, modifier = Modifier.fillMaxWidth())''',
'''                    OutlinedTextField(value = endpointDraft, onValueChange = { endpointDraft = it },
                        label = { Text("https://your-backend.example.com") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(value = clientTokenDraft, onValueChange = { clientTokenDraft = it },
                        label = { Text("JARVIS client token") }, singleLine = true,
                        visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth())''')
s = s.replace('onSaveAiBackendEndpoint(endpointDraft); showAiBackendDialog = false',
              'onSaveAiBackendEndpoint(endpointDraft, clientTokenDraft); clientTokenDraft = ""; showAiBackendDialog = false')
# Keep only one declaration of the dialog token state.
lines = s.splitlines()
seen_decl = False
out = []
for line in lines:
    if "var clientTokenDraft by remember" in line:
        if seen_decl:
            continue
        seen_decl = True
    out.append(line)
s = "\n".join(out) + "\n"
if "clientTokenDraft" not in s or "onSaveAiBackendEndpoint(endpointDraft, clientTokenDraft)" not in s:
    raise RuntimeError("Failed to patch VoiceChatScreen token input")
screen.write_text(s)

container = root / "app/src/main/java/com/example/ui/screens/JarvisMainContainer.kt"
s = container.read_text()
s = s.replace('onSaveAiBackendEndpoint = { viewModel.saveAiBackendEndpoint(it) }',
              'onSaveAiBackendEndpoint = { endpoint, token -> viewModel.saveAiBackendEndpoint(endpoint, token) }')
container.write_text(s)
print("Patched JARVIS Android app to save the private client token and send it to the backend.")
