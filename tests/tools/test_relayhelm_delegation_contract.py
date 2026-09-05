"""Relayhelm's user choice, model fidelity and truthful terminal-result contracts."""
import json
from types import SimpleNamespace

import pytest

from tools import delegate_tool
from tools.delegate_tool_child_run import _SchemaOutcome, _build_result_entry, _fabricated_entry
from tools.delegate_tool_config import _resolve_child_runtime
from tools.registry import registry


@pytest.fixture
def parent(monkeypatch):
    monkeypatch.setattr(delegate_tool, '_load_config', lambda: {})
    monkeypatch.setattr(delegate_tool, '_get_max_spawn_depth', lambda: 2)
    monkeypatch.setattr(delegate_tool, '_get_max_concurrent_children', lambda: 3)
    monkeypatch.setattr(delegate_tool, 'is_spawn_paused', lambda: False)
    return SimpleNamespace(model='selected-model', _delegate_depth=0, clarify_callback=None)


@pytest.mark.parametrize('answer', [None, 'Keep one agent', 'yes', True, ''])
def test_model_supplied_consent_cannot_authorize_spawn(parent, monkeypatch, answer):
    parent.clarify_callback = (lambda question, choices: answer) if answer is not None else None
    def unexpected_spawn(*args, **kwargs):
        pytest.fail('Child created without exact user split choice')
    monkeypatch.setattr(delegate_tool, '_build_children', unexpected_spawn)
    response = json.loads(registry.dispatch('delegate_task', {
        'tasks': [{'goal': 'Inspect module a'}, {'goal': 'Inspect module b'}], 'consent': True,
    }, parent_agent=parent))
    assert response.get('status') == 'not_started', response
    assert response['completed'] is False
    assert response['error']


def test_user_choice_covers_actual_model_and_goals(parent, monkeypatch):
    shown = []
    def choose(question, choices):
        shown.append((question, choices))
        return 'Split task'
    parent.clarify_callback = choose
    monkeypatch.setattr(delegate_tool, '_build_children', lambda *args, **kwargs: ([], None))
    monkeypatch.setattr(delegate_tool, '_announce_batch', lambda *args: None)
    monkeypatch.setattr(delegate_tool, '_run_batch', lambda batch, background: json.dumps({'started': True}))
    result = json.loads(registry.dispatch('delegate_task', {
        'tasks': [{'goal': 'Inspect module a'}, {'goal': 'Inspect module b'}],
    }, parent_agent=parent))
    assert result.get('started') is True, result
    assert len(shown) == 1
    assert 'selected-model' in shown[0][0]
    assert 'Inspect module a' in shown[0][0] and 'Inspect module b' in shown[0][0]
    assert 'Split task' in shown[0][1]


@pytest.mark.parametrize('model', [None, 'chosen-child'])
def test_child_cannot_silently_fall_back_to_another_model(model):
    parent = SimpleNamespace(model='chosen-parent', provider='openai', base_url='https://api.openai.com/v1',
                             reasoning_config={'effort': 'medium'}, _fallback_chain=[{'model': 'other'}])
    runtime = _resolve_child_runtime(parent, {}, 'test-key', model=model, override_provider=None,
        override_base_url=None, override_api_key=None, override_api_mode=None, override_max_tokens=None,
        override_acp_command=None, override_acp_args=None)
    assert runtime['model'] == (model or 'chosen-parent')
    assert runtime['fallback_model'] is None
    assert runtime['reasoning_config'] == parent.reasoning_config


@pytest.mark.parametrize('result,reason', [
    ({'completed': False, 'final_response': 'Partial work'}, 'iteration budget'),
    ({'completed': True, 'failed': True, 'error': 'Provider rejected model', 'final_response': 'Partial'}, 'Provider rejected'),
    ({'completed': True, 'failure_reason': 'billing', 'final_response': 'Partial'}, 'billing'),
    ({'completed': True, 'status': 'failed', 'error': 'Tests failed', 'final_response': 'Done'}, 'Tests failed'),
])
def test_failed_work_never_reports_completed(result, reason):
    entry = _build_result_entry(SimpleNamespace(model='selected-model'), result, 0, 1, _SchemaOutcome(None, None, [], 0))
    assert entry['status'] == 'failed'
    assert entry['completed'] is False
    assert reason in entry['failure_reason']
    assert entry['summary'] == result['final_response']


def test_success_and_exceptions_have_unambiguous_completion():
    entry = _build_result_entry(SimpleNamespace(model='selected-model'),
        {'completed': True, 'final_response': 'Tests passed', 'messages': []}, 0, 1, _SchemaOutcome(None, None, [], 0))
    assert entry['status'] == 'completed' and entry['completed'] is True
    failed = _fabricated_entry(0, 'error', 'Connection closed', None)
    assert failed['status'] == 'failed'
    assert failed['completed'] is False
    assert failed['failure_reason'] == 'Connection closed'


def test_schema_retry_cannot_hide_provider_failure():
    from tools.delegate_tool_child_run import _validate_child_output_schema
    child = SimpleNamespace(model='selected-model', _delegate_output_schema={
        'type': 'object', 'required': ['answer'], 'properties': {'answer': {'type': 'string'}},
    })
    child.run_conversation = lambda **kwargs: {
        'final_response': '{"answer": "partial"}', 'completed': False,
        'failed': True, 'error': 'Stream failed', 'failure_reason': 'transport_error',
    }
    result = {'final_response': 'invalid json', 'completed': True, 'messages': []}
    schema = _validate_child_output_schema(child, result, 0, 'task', None)
    entry = _build_result_entry(child, result, 0, 1, schema)
    assert schema.valid is True
    assert entry['completed'] is False
    assert entry['status'] == 'failed'
    assert entry['failure_reason'] == 'transport_error'


def test_provider_model_substitution_refuses_unstarted_child(parent, monkeypatch):
    import run_agent
    closed = []
    child = SimpleNamespace(model='substitute-model', close=lambda: closed.append(True))
    monkeypatch.setattr(run_agent, 'AIAgent', lambda **kwargs: child)
    monkeypatch.setattr(delegate_tool, '_resolve_child_runtime', lambda *args, **kwargs: {
        'model': 'selected-model', 'provider': 'openai', 'base_url': 'https://api.openai.com/v1',
    })
    monkeypatch.setattr(delegate_tool, '_resolve_child_toolsets', lambda *args: ([], []))
    monkeypatch.setattr(delegate_tool, '_build_child_progress_callback', lambda *args, **kwargs: None)
    monkeypatch.setattr(delegate_tool, '_open_child_session_db', lambda *args: None)
    with pytest.raises(ValueError, match='substitute-model'):
        delegate_tool._build_child_agent(0, 'Inspect the module', None, None, 'selected-model', 5, 1, parent)
    assert closed == [True]
