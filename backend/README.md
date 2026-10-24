# JARVIS AI backend

This server connects the original JARVIS Android project to the OpenAI Responses API. The OpenAI API key stays on the server and must never be placed in the APK or pasted into a chat.

## Deploy on Render

1. Push this repository to GitHub (the backend folder is in this repo).
2. In Render, create a **Web Service** from this repository.
3. Set **Root Directory** to `backend`, **Build Command** to `npm install`, and **Start Command** to `npm start`.
4. Add environment variables in the hosting dashboard:
   - `OPENAI_API_KEY`: your newly created OpenAI API key.
   - `JARVIS_CLIENT_TOKEN`: a long, random secret of at least 32 characters. Generate it privately; do not share it in chat or commit it to GitHub.
   - Optional `OPENAI_MODEL`: defaults to `gpt-4.1-mini`.
5. Deploy. Copy the service's HTTPS base URL.
6. In JARVIS, open Voice/Chat and tap the cloud icon. Enter the HTTPS base URL and the same `JARVIS_CLIENT_TOKEN`, then Save.
7. Open `https://YOUR-SERVICE/health` to check the service is running. The health endpoint reports whether server secrets are configured, but never returns the secrets.

## Local testing

Requires Node.js 20+. Run `npm install`, then set `OPENAI_API_KEY` and `JARVIS_CLIENT_TOKEN` in your local shell environment and run `npm start`. Do not put real values in source files.

## Safety and limits

- Set a usage/spending limit in the OpenAI Platform.
- This backend validates the client token and only returns a small allowlist of Android actions.
- JARVIS still needs Android permissions/Phone Control enabled for supported actions.
- This is a prototype. Do not expose it publicly without monitoring, rate limiting, and rotating the client token if it leaks.
