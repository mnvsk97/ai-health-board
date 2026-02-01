# Issues With Bot To Bot Testing

Date: 2026-02-01

Summary:
Bot-to-bot voice testing over Daily in Pipecat Cloud is unstable. Tests consistently stalled after the initial prompt, transcripts stopped advancing, and several transport/STT errors appeared intermittently.

What happened:
- Audio did not reliably flow between the tester and intake agents.
- The tester often only heard or transcribed itself, not the other agent.
- Transcripts frequently contained only the first tester prompt and at most one intake response.

Observed symptoms:
- Daily transcription errors when the participant was not an owner: UserMustBeAdmin.
- Invalid RTVI transport message warnings repeated during sessions.
- OpenAI STT errors when the model was not authorized for the account.
- Inconsistent session startup and log availability across runs.

Root causes suspected:
- Daily transcription requires owner permissions; cloud-issued tokens are not always owner.
- Bot-to-bot audio routing is brittle without explicit participant track capture and reliable user_id binding.
- STT model authorization mismatches on the Truefoundry gateway.

Current status:
- Bot-to-bot voice testing is flaky and not reliable enough for the demo.
- Changes made for the experiment have been rolled back.

Recommendation:
- Use text-based testing for the demo.
- If voice testing is required, coordinate with Daily/Pipecat support for owner token behavior and RTVI message validation, and verify STT model access in the gateway.
