"""Tools available exclusively to scoped Career runs."""
from waku.tools.registry import Tool


def make_submit_tool(submit):
    def execute(profile):
        submit(profile)
        return 'Career profile proposal validated. The coordinator can save it in state.db after this stage completes.'

    return Tool('submit_stage_result', 'Submit the normalized career profile for validation.',
                {'type': 'object', 'properties': {'profile': {'type': 'object',
                 'properties': {'basic': {'type': 'object'}, 'records': {'type': 'array',
                 'items': {'type': 'object', 'properties': {
                     'source_id': {'type': 'string'}, 'title': {'type': 'string'},
                     'description': {'type': 'string'},
                     'skills': {'type': 'array', 'items': {'type': 'string'}}},
                     'required': ['source_id', 'title', 'description', 'skills']}}},
                 'required': ['basic', 'records']}}, 'required': ['profile']}, execute)
