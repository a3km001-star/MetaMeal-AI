from ai import agent


def test_run_chat_retries_empty_assistant_response(monkeypatch):
	responses = iter(
		[
			{"choices": [{"message": {"role": "assistant", "content": ""}}]},
			{
				"choices": [
					{
						"message": {
							"role": "assistant",
							"content": "Approximate nutrition: 620 kcal per serving.",
						},
					}
				]
			},
		]
	)
	call_tools = []

	monkeypatch.setattr(agent, "_load_history", lambda *args, **kwargs: [])
	monkeypatch.setattr(agent, "_save_message", lambda *args, **kwargs: None)
	monkeypatch.setattr(agent, "_call_groq", lambda messages, tools: call_tools.append(tools) or next(responses))

	reply, tool_calls = agent.run_chat("Calculate this recipe", "user-1")

	assert reply == "Approximate nutrition: 620 kcal per serving."
	assert tool_calls == []
	assert call_tools == [agent.get_tool_definitions(), None]