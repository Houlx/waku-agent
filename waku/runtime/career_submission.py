"""Matching-only submission protocol; evidence and semantic validation stay separate."""
from types import SimpleNamespace

import anthropic

from waku.loop.models import OpenAICompatClient
from waku.runtime.career_matching import MATCHING_INPUT_BUDGET_BYTES, matching_input_bytes

RECOVERY_INSTRUCTION = ('Submit the complete matching result now using submit_stage_result. '
                        'Do not return prose.')
MISSING_SUBMISSION = ('Career matching ended without a structured submission. '
                      'Please retry Analyze Job; no new match report was saved.')
TRUNCATED_SUBMISSION = ('Career matching output was truncated before structured submission completed. '
                        'Please retry Analyze Job or choose a model that can complete the structured output; '
                        'no new match report was saved.')


class MatchingSubmission:
    """Force full-mode submission when supported; allow one no-tool correction."""

    def __init__(self, client, coverage, captured, observe):
        self.client = client
        self.coverage = coverage
        self.captured = captured
        self.observe = observe
        self.recovered = False
        self.truncated = False
        self.force_supported = isinstance(client, (OpenAICompatClient, anthropic.Anthropic))
        self.system = None
        self.tools = None
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.system = kwargs.get('system')
        self.tools = kwargs.get('tools')
        force = self.force_supported and self.coverage.mode == 'full' and not self.captured()
        if not force:
            return self.client.messages.create(**kwargs)
        choice = ({'type': 'function', 'function': {'name': 'submit_stage_result'}}
                  if isinstance(self.client, OpenAICompatClient)
                  else {'type': 'tool', 'name': 'submit_stage_result'})
        try:
            return self.client.messages.create(**kwargs, tool_choice=choice)
        except Exception as exc:
            # Retry only an explicit unsupported tool-choice request. Never hide
            # authentication, transport, context-budget or unrelated API errors.
            message = str(exc).casefold()
            if (getattr(exc, 'status_code', None) not in {400, 422}
                    or not any(term in message for term in ('tool_choice', 'tool choice'))
                    or not any(term in message for term in ('not supported', 'unsupported', 'does not support', 'not allowed', 'only', 'invalid'))):
                raise
            self.force_supported = False
            self.observe({'event': 'tool_choice_unsupported'})
            return self.client.messages.create(**kwargs)

    def on_no_tools(self, response, messages, remaining):
        if self.captured():
            return False  # Preserve accepted state and the existing final confirmation.
        raw = getattr(response, 'raw_stop_reason', None) or response.stop_reason
        self.truncated = self.truncated or raw in {'length', 'max_tokens'}
        if raw not in {'length', 'max_tokens', 'stop', 'end_turn', 'stop_sequence'}:
            raise ValueError('Career matching provider stopped before structured submission '
                             f'(termination: {raw}). Please retry Analyze Job or choose another model.')
        if self.recovered or remaining <= 0:
            raise ValueError(TRUNCATED_SUBMISSION if self.truncated else MISSING_SUBMISSION)
        self.coverage.assert_current()
        # Only this no-tool response has no usable stage state. Keep the checked
        # initial context and every earlier tool call/result, including delivery.
        messages.pop()
        messages.append({'role': 'user', 'content': RECOVERY_INSTRUCTION})
        if matching_input_bytes(self.system, messages, self.tools) > MATCHING_INPUT_BUDGET_BYTES:
            if self.truncated:
                raise ValueError(TRUNCATED_SUBMISSION)
            raise ValueError('Career matching cannot safely retry structured submission within the input budget. '
                             'Please retry Analyze Job; no new match report was saved.')
        self.recovered = True
        self.observe({'event': 'submit_only_recovery', 'raw_stop_reason': raw,
                      'remaining_iterations': remaining})
        return True
