"""Calculate conditional BGM gains. Does not measure audio or edit a project."""
import argparse
import json
import math


def finite_range(value, lower, upper, name):
    number = float(value)
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f'{name} must be finite and within [{lower}, {upper}]')
    return number


def plan(voice_lufs, music_lufs, gap_lu, *, basis, voice_peak=None,
         music_peak=None, peak_ceiling=-1.5):
    voice = finite_range(voice_lufs, -70, 10, 'voice_lufs')
    music = finite_range(music_lufs, -70, 10, 'music_lufs')
    gap = finite_range(gap_lu, 0, 40, 'gap_lu')
    ceiling = finite_range(peak_ceiling, -20, 0, 'peak_ceiling')
    if basis not in ('conditional_normalized', 'user_supplied_measurements'):
        raise ValueError('Unknown calculation basis')
    target = voice - gap
    gain = target - music
    result = {
        'basis': basis,
        'audio_measured_by_this_script': False,
        'voice_reference_lufs': round(voice, 3),
        'music_baseline_lufs_before_new_gain': round(music, 3),
        'dialogue_gap_lu': round(gap, 3),
        'music_target_lufs_estimate': round(target, 3),
        'music_gain_to_apply_db': round(gain, 3),
        'peak_ceiling_reference_dbtp': ceiling,
        'conditions': [
            'Music baseline must be before the gain being calculated.',
            'Compare matching active windows and channel layouts.',
            'Linear gain only; no later normalization, limiting or clipping assumed.',
            'Export and measure the final mix; dialogue intelligibility still requires listening.',
        ],
        'peak_check': {'status': 'not_evaluated_missing_input_peaks'},
    }
    if basis == 'conditional_normalized':
        result['conditions'].insert(0, 'Normalization-before-gain order is assumed, not verified in Jianying.')
    # A sum-of-amplitudes bound is intentionally not labelled a measured mix peak.
    if voice_peak is not None:
        vp = finite_range(voice_peak, -120, 30, 'voice_peak')
    else:
        vp = None
    if music_peak is not None:
        mp = finite_range(music_peak, -120, 30, 'music_peak')
    else:
        mp = None
    if vp is not None and mp is not None:
        adjusted = mp + gain
        bound = 20 * math.log10(10 ** (vp / 20) + 10 ** (adjusted / 20))
        result['peak_check'] = {
            'status': 'conservative_two_track_bound_only',
            'voice_peak_input_dbtp': vp,
            'music_peak_input_dbtp': mp,
            'music_peak_after_gain_estimate_dbtp': round(adjusted, 3),
            'simultaneous_same_polarity_peak_bound_dbtp': round(bound, 3),
            'master_trim_to_meet_bound_db': round(min(0.0, ceiling - bound), 3),
            'bound_exceeds_reference': bound > ceiling,
            'actual_mix_peak_measured': False,
            'excludes_other_tracks': True,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='mode', required=True)
    normalized = subs.add_parser('normalized', help='Conditional normalize-then-gain estimate')
    normalized.add_argument('--voice-normalized-lufs', type=float, default=-23)
    normalized.add_argument('--voice-gain-db', type=float, default=10)
    normalized.add_argument('--music-normalized-lufs', type=float, default=-23)
    measured = subs.add_parser('measured', help='Use externally measured final voice and pre-gain music')
    measured.add_argument('--voice-lufs', type=float, required=True)
    measured.add_argument('--music-lufs', type=float, required=True)
    measured.add_argument('--voice-true-peak', type=float)
    measured.add_argument('--music-true-peak', type=float)
    for sub in (normalized, measured):
        sub.add_argument('--gap-lu', type=float, required=True)
        sub.add_argument('--peak-ceiling', type=float, default=-1.5)
    args = parser.parse_args()
    try:
        if args.mode == 'normalized':
            base = finite_range(args.voice_normalized_lufs, -70, 0, 'voice_normalized_lufs')
            vg = finite_range(args.voice_gain_db, -60, 30, 'voice_gain_db')
            result = plan(base + vg, args.music_normalized_lufs, args.gap_lu,
                          basis='conditional_normalized', peak_ceiling=args.peak_ceiling)
            result['normalization_assumptions'] = {
                'voice_normalized_lufs': base, 'voice_gain_db': vg,
                'music_normalized_lufs': args.music_normalized_lufs,
            }
        else:
            result = plan(args.voice_lufs, args.music_lufs, args.gap_lu,
                          basis='user_supplied_measurements',
                          voice_peak=args.voice_true_peak,
                          music_peak=args.music_true_peak, peak_ceiling=args.peak_ceiling)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OverflowError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
