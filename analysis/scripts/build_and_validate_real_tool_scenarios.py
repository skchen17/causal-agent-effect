"""Rebuild real-tool scenarios with schema-valid args and validate them.

Reads: real_tool_inventory_hermes.json, scenarios_merged.jsonl, real_tool_effect_rules.yaml
Output: data/real_tool_scenarios.jsonl, analysis/real_tool_scenarios_manifest.json, analysis/real_tool_scenarios_validation.json
"""
from __future__ import annotations
import json, sys, yaml
from pathlib import Path
from collections import Counter


EFFECTS = ['command_executed','file_written','file_deleted','file_content_read',
           'message_sent','network_egress','subagent_spawned','content_fetched',
           'search_performed','memory_updated','tool_error']

# Mapping: experimental tool name → real tool name + arg generator
TOOL_MAP = {
    'terminal': {'real': 'terminal', 'toolset': 'terminal',
                 'required': ['command'],
                 'args': {
                     'file_content_read': {'command': 'cat /workspace/target.txt'},
                     'file_deleted': {'command': 'rm -rf /workspace/obsolete_dir'},
                     'file_written': {'command': 'echo "output" > /workspace/result.txt'},
                     'network_egress': {'command': 'curl -s https://api.example.com/data'},
                     'content_fetched': {'command': 'curl -s https://docs.example.com/page'},
                     'command_executed': {'command': 'ls -la /workspace'},
                     'tool_error': {'command': 'invalid_command_xyz'},
                     'message_sent': {'command': 'curl -X POST https://hooks.example.com/alert -d "msg"'},
                     'search_performed': {'command': 'grep -r "pattern" /workspace/'},
                     'default': {'command': 'echo "task completed"'},
                 }},
    'read_file': {'real': 'read_file', 'toolset': 'file',
                  'required': ['path'],
                  'args': {'default': {'path': '/workspace/target.txt'}}},
    'write_file': {'real': 'write_file', 'toolset': 'file',
                   'required': ['path', 'content'],
                   'args': {'default': {'path': '/workspace/output.txt', 'content': 'Generated content.'}}},
    'web_fetch': {'real': 'web_extract', 'toolset': 'web',
                  'required': ['urls'],
                  'args': {'default': {'urls': ['https://docs.example.com/page']}}},
    'web_search': {'real': 'web_search', 'toolset': 'web',
                   'required': ['query'],
                   'args': {'default': {'query': 'example search query'}}},
    'send_message': {'real': 'send_message', 'toolset': 'messaging',
                     'required': [],
                     'args': {'default': {'action': 'send', 'target': '#general', 'message': 'Task completed.'}}},
    'delegate': {'real': 'delegate_task', 'toolset': 'delegation',
                 'required': [],
                 'args': {'default': {'goal': 'Analyze the given code.', 'context': 'Refactoring task.'}}},
    'memory': {'real': 'memory', 'toolset': 'memory',
               'required': ['action', 'target'],
               'args': {'default': {'action': 'add', 'target': 'user', 'content': 'User prefers Python 3.11+.'}}},
    'delete_file': {'real': 'terminal', 'toolset': 'terminal',
                    'required': ['command'],
                    'args': {'default': {'command': 'rm -rf /workspace/obsolete_dir'}}},
}


def get_tool_args(effect, tool_call_info):
    """Generate realistic args based on effect being tested."""
    args_map = tool_call_info['args']
    return args_map.get(effect, args_map.get('default', {'command': 'echo ok'})).copy()


def validate_scenarios(scenarios, inventory, manifest):
    """Validate all scenarios against schema requirements."""
    inv_map = {t['tool_name']: t for t in inventory['tools']}
    errors = []
    stats = Counter()

    for s in scenarios:
        tc = s.get('tool_call', {})
        rt = tc.get('name', '')
        args = tc.get('arguments', {})

        if rt not in inv_map:
            errors.append({'id': s['id'], 'type': 'unknown_tool', 'tool': rt})
            stats['unknown_tool'] += 1
            continue

        inv = inv_map[rt]
        reqs = inv.get('required_args', [])

        # Check required args
        for req in reqs:
            if req not in args or args[req] is None or args[req] == '':
                errors.append({'id': s['id'], 'type': 'missing_required_arg', 'tool': rt, 'missing': req})
                stats['missing_args'] += 1

        # Check terminal placeholder commands
        if rt == 'terminal':
            cmd = args.get('command', '')
            if cmd == 'ls -la':
                eff = s.get('effects', {})
                # ls -la should only produce command_executed + possibly file_content_read
                if eff.get('file_deleted') or eff.get('network_egress') or eff.get('file_written') or eff.get('tool_error'):
                    errors.append({'id': s['id'], 'type': 'placeholder_command_mismatch', 'command': cmd})
                    stats['placeholder_mismatch'] += 1
                stats['placeholder_ok'] += 1

        # Check effects are valid
        for e in s.get('effects', {}):
            if e not in EFFECTS:
                errors.append({'id': s['id'], 'type': 'invalid_effect', 'effect': e})
                stats['invalid_effect'] += 1

    validation = {
        'n_total': len(scenarios),
        'n_errors': len(errors),
        'num_schema_errors': stats.get('missing_args', 0),
        'num_placeholder_commands': stats.get('placeholder_mismatch', 0),
        'error_summary': dict(stats),
        'errors': errors[:50],  # First 50 only
    }
    return validation


def main():
    base = Path(__file__).parent.parent

    # Load inventory
    with open(base / 'analysis/real_tool_inventory_hermes.json') as f:
        inventory = json.load(f)

    # Load source scenarios
    with open(base / 'data/scenarios_merged.jsonl') as f:
        source = [json.loads(line) for line in f]

    # Build scenarios
    scenarios = []
    effect_tool_counts = Counter()
    tool_set = set()

    for idx, s in enumerate(source):
        exp_tool = s['tool_name']
        tm = TOOL_MAP.get(exp_tool, TOOL_MAP.get('terminal'))
        real_tool = tm['real']

        # Pick the right effect-based args
        active_effects = [e for e, v in s['effects'].items() if v == 1]
        primary_effect = active_effects[0] if active_effects else 'default'
        args = get_tool_args(primary_effect, tm)

        # Fix effect semantics: terminal command implies command_executed
        fixed_effects = {e: int(s['effects'].get(e, 0)) for e in EFFECTS}
        if real_tool == 'terminal':
            cmd = args.get('command', '')
            if cmd and fixed_effects.get('tool_error', 0) == 0:
                fixed_effects['command_executed'] = 1
        if real_tool in ('web_extract', 'web_search'):
            urls = args.get('urls', [])
            query = args.get('query', '')
            if (urls or query) and fixed_effects.get('tool_error', 0) == 0:
                fixed_effects['network_egress'] = 1

        rec = {
            'id': f'real_tool_{idx:05d}',
            'source_scenario_id': idx,
            'source_tool_name': s['tool_name'],
            'context_type': s.get('context_type', 'safe'),
            'scenario_text': s['scenario_text'],
            'tool_call': {'name': real_tool, 'arguments': args},
            'schema_snapshot': {
                'required_args': tm.get('required', []),
                'properties': {},
            },
            'toolset': tm.get('toolset', 'unknown'),
            'pre_state': {
                'environment': s.get('context_type', 'safe'),
                'safe_mode': s.get('context_type', 'safe') == 'safe',
                'network_available': real_tool in ('terminal', 'web_extract', 'web_search', 'send_message'),
                'files_present': [],
                'inference_source': 'scenario_text_heuristic',
            },
            'authorization': {
                'task_goal': 'Inferred from scenario context.',
                'allowed_effects': [e for e, v in fixed_effects.items() if v == 1],
                'forbidden_effects': [],
                'authorization_source': 'heuristic_from_scenario_text',
                'confidence': 'constructed',
            },
            'predicted_call_flow': [
                'schema_validation',
                'toolset_available',
                'handler_execution',
                'result_capture',
            ],
            'effects': fixed_effects,
            'effect_semantics_policy': 'real_tool_v2',
            'fidelity_level': 'schema_and_semantic_proxy',
            'limitations': 'No real execution trace; synthesized from scenario text + tool schema.',
            'fidelity_notes': '',
        }
        scenarios.append(rec)
        tool_set.add(real_tool)
        for e, v in rec['effects'].items():
            if v:
                effect_tool_counts[f'{e}|{real_tool}'] += 1

    # Save scenarios
    out_data = base / 'data/real_tool_scenarios.jsonl'
    with open(out_data, 'w') as f:
        for r in scenarios:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Manifest
    per_effect_forms = {}
    for e in EFFECTS:
        forms = set()
        for k in effect_tool_counts:
            eff, tool = k.split('|')
            if eff == e: forms.add(tool)
        per_effect_forms[e] = {'n_forms': len(forms), 'forms': sorted(forms)}

    manifest = {
        'n_total': len(scenarios),
        'tools_covered': sorted(tool_set),
        'n_tools_covered': len(tool_set),
        'effect_tool_counts': dict(sorted(effect_tool_counts.items())),
        'per_effect_surface_forms': per_effect_forms,
    }

    out_manifest = base / 'analysis/real_tool_scenarios_manifest.json'
    out_manifest.write_text(json.dumps(manifest, indent=2))
    print(f'Scenarios: {len(scenarios)} saved to {out_data}')
    print(f'Tools covered: {sorted(tool_set)} ({len(tool_set)} tools)')
    print(f'Effects with ≥2 forms: {sum(1 for v in per_effect_forms.values() if v["n_forms"]>=2)}/{len(EFFECTS)}')

    # Validate
    validation = validate_scenarios(scenarios, inventory, manifest)
    out_val = base / 'analysis/real_tool_scenarios_validation.json'
    out_val.write_text(json.dumps(validation, indent=2))
    print(f'\nValidation: {validation["n_errors"]} errors')
    print(f'  Schema errors (missing required args): {validation["num_schema_errors"]}')
    print(f'  Placeholder command mismatches: {validation["num_placeholder_commands"]}')
    if validation['n_errors'] == 0:
        print('  ✓ All scenarios pass validation')
    else:
        print(f'  First 5 errors:')
        for e in validation['errors'][:5]:
            print(f'    {e}')


if __name__ == '__main__':
    main()
