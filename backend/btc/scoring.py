"""Rule-based confidence. Points in, High / Medium / Low out, with the reasons written down."""


def score(match, label, hops, weak_change, unresolved_splits, history_truncated):
    points, reasons = 0, []
    if match == 'label':
        points += 3
        reasons.append('+3 The reached address itself has an exchange label')
    elif match == 'cluster':
        points += 2
        reasons.append('+2 The address was spent together with a labeled address (same-owner rule)')
    else:
        points += 1
        reasons.append('+1 No label. Pattern only: many senders, then sweeps to one output')
    if match != 'pattern':
        if label.get('verified'):
            points += 3
            reasons.append('+3 The label source is marked verified')
        else:
            points += 1
            reasons.append('+1 The label source is not verified')
    hop_points = 3 if hops == 0 else 2 if hops == 1 else 1 if hops == 2 else 0
    points += hop_points
    reasons.append(f'+{hop_points} Found {hops} hop(s) from the seed')
    if weak_change:
        points -= weak_change
        reasons.append(f'-{weak_change} Followed {weak_change} weak change guess(es) on the path')
    if unresolved_splits:
        points -= 2 * unresolved_splits
        reasons.append(f'-{2 * unresolved_splits} Path crossed {unresolved_splits} split(s) where change could not be told from payment')
    if history_truncated:
        points -= 1
        reasons.append('-1 History of the reached address was cut off by the transaction limit')
    level = 'High' if points >= 7 else 'Medium' if points >= 3 else 'Low'
    if match == 'pattern' and level != 'Low':
        level = 'Low'
        reasons.append('Capped at Low: a pattern without a label is only a pointer')
    return level, points, reasons
