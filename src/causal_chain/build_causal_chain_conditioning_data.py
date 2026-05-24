"""Build causal-chain conditioning data with 5 conditions per sample.

Conditions: raw, tool_only, effect_chain, task_causal_chain, wrong_chain.
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

EFFECT_NAMES = ['command_executed','file_written','file_deleted','file_content_read',
                'message_sent','network_egress','subagent_spawned','content_fetched',
                'search_performed','memory_updated','tool_error']

def make_wrong_chain(effects, effect_name, condition_type, source_text, tool_name, rng):
    """Create wrong-chain text with plausible but incorrect effect statements."""
    active = [e for e, v in effects.items() if v == 1]
    inactive = [e for e, v in effects.items() if v == 0 and e != effect_name]

    wrong_text = source_text
    if condition_type == 'effect_omission' and active:
        omit = rng.choice(active)
        wrong_text += f' [STATED EFFECTS: {", ".join(e for e in active if e != omit)}. Note: {omit} is NOT listed as an effect.]'
        return wrong_text, {omit: 0}, None
    elif condition_type == 'effect_flip' and inactive:
        flip = rng.choice(inactive)
        stated = list(active) + [flip]
        wrong_text += f' [STATED EFFECTS: {", ".join(stated)}. The listed effect "{flip}" contradicts the actual tool behavior.]'
        return wrong_text, {flip: 1}, None
    elif condition_type == 'authorization_flip':
        forbidden = active if active else [effect_name]
        wrong_text += (
            f' [AUTHORIZATION CHAIN: The task authorization is incorrectly stated as allowing '
            f'{", ".join(forbidden)}, even though those effects should be treated as forbidden for this diagnostic.]'
        )
        stated_auth = {
            'allowed_effects': list(forbidden),
            'forbidden_effects': [e for e in effects if e not in forbidden],
            'authorization_valid': False,
        }
        return wrong_text, {}, stated_auth
    return source_text, {}, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='data/scenarios_merged.jsonl')
    p.add_argument('--output', default='data/causal_chain_conditioning.jsonl')
    p.add_argument('--manifest', default='analysis/causal_chain_conditioning_manifest.json')
    p.add_argument('--typed-wrong-chain', action='store_true')
    args = p.parse_args()

    base = Path(__file__).resolve().parent.parent
    with open(base / args.input) as f:
        scenarios = [json.loads(line) for line in f]

    rng = random.Random(42)
    outputs = []
    effects_covered = set()

    for s in scenarios:
        t_n = s['tool_name']
        active_effects = [e for e, v in s['effects'].items() if v == 1]
        if not active_effects:
            continue
        eff = active_effects[0]  # Pick first active effect for conditioning
        effects_covered.add(eff)
        base_text = s['scenario_text']

        # 5 conditions
        for cond in ['raw', 'tool_only', 'effect_chain', 'task_causal_chain', 'wrong_chain']:
            wrong_chain_type = None
            stated_authorization = None
            if cond == 'raw':
                text = base_text
                wrong_info = {}
            elif cond == 'tool_only':
                text = f'Tool: {t_n}. Action: execute standard {t_n} operation as described in the scenario.'
                wrong_info = {}
            elif cond == 'effect_chain':
                eff_str = ', '.join(active_effects)
                text = f'{base_text} [CAUSAL CHAIN: {t_n} call -> immediate operation -> causal effects: {eff_str}]'
                wrong_info = {}
            elif cond == 'task_causal_chain':
                eff_str = ', '.join(active_effects)
                text = f'Task: perform {t_n} operation. Authorized effects: {eff_str}. Tool: {t_n}. Observed effects: {eff_str}. Consistency: valid'
                wrong_info = {}
            elif cond == 'wrong_chain':
                if args.typed_wrong_chain:
                    candidates = ['authorization_flip']
                    if active_effects:
                        candidates.append('effect_omission')
                    if any(v == 0 for e, v in s['effects'].items() if e != eff):
                        candidates.append('effect_flip')
                    wrong_chain_type = candidates[len(outputs) % len(candidates)]
                else:
                    wrong_chain_type = 'effect_omission' if rng.random() < 0.5 else 'effect_flip'
                text, wrong_info, stated_authorization = make_wrong_chain(s['effects'], eff, wrong_chain_type, base_text, t_n, rng)

            row = {
                'id': f'chain-{len(outputs):06d}',
                'base_id': len(outputs) // 5,
                'condition': cond,
                'tool_name': t_n,
                'scenario_text': text,
                'effects': s['effects'],
                'stated_effects': {**s['effects'], **wrong_info} if wrong_info else None,
                'chain_valid': cond != 'wrong_chain',
            }
            if cond == 'wrong_chain':
                row['wrong_chain_type'] = wrong_chain_type
            if stated_authorization is not None:
                row['stated_authorization'] = stated_authorization
            outputs.append(row)

    out = base / args.output
    with open(out, 'w') as f:
        for o in outputs:
            f.write(json.dumps(o, ensure_ascii=False) + '\n')

    # Manifest
    wrong_chain_counts = {}
    for o in outputs:
        if o.get('condition') == 'wrong_chain':
            key = o.get('wrong_chain_type', 'none')
            wrong_chain_counts[key] = wrong_chain_counts.get(key, 0) + 1
    manifest = {'n_total': len(outputs), 'n_per_condition': len(outputs)//5, 'effects_covered': sorted(effects_covered),
                'conditions': ['raw','tool_only','effect_chain','task_causal_chain','wrong_chain'],
                'typed_wrong_chain': args.typed_wrong_chain,
                'wrong_chain_type_counts': wrong_chain_counts}
    manifest_out = base / args.manifest
    manifest_out.write_text(json.dumps(manifest, indent=2))
    print(f'Saved {len(outputs)} chain-conditioned samples to {out}')
    print(f'Effects covered: {sorted(effects_covered)}')


if __name__ == '__main__':
    main()
