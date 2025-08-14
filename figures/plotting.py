from analysis import get_margin_stats
import polars as pl
from polars import col as c
from config import FIGURE_DIR
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from pathlib import Path
from figures.plotting_prep import prepare_quantile_distribution


def plot_price_distribution(min_quantile: int = 1, max_quantile: int = 99, output: Path | None = None) -> Path:
    """Create a publication-quality chart of margin distribution & cumulative margin.

    Features:
      - Bars: margin threshold (per-quantile margin_over_nadac value)
      - Line: cumulative margin across quantiles
      - Reference lines: mean & median margin_over_nadac
      - Annotations: first profitable prescription & cumulative break-even
    """
    FIGURE_DIR.mkdir(exist_ok=True, parents=True)
    if output is None:
        output = FIGURE_DIR / 'price_distribution.png'

    df = prepare_quantile_distribution(min_quantile, max_quantile).to_pandas()
    stats = get_margin_stats()
    mean_val = stats['mean_margin_over_nadac'][0]
    median_val = stats['median_margin_over_nadac'][0]

    plt.rcParams.update({
        # Typography
        'font.family': 'sans-serif',
        'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica', 'Liberation Sans', 'Noto Sans'],
        'font.size': 12,
        'axes.titlesize': 18,
        'axes.titleweight': 'semibold',
        'axes.labelsize': 13,
        'legend.fontsize': 11,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,

        # Colors & background
        'axes.facecolor': '#f9f9fb',
        'figure.facecolor': 'white',
        'axes.edgecolor': '#CCCCCC',
        'grid.color': '#DDDDDD',

        # Rendering
        'figure.dpi': 220,
    })

    fig, ax1 = plt.subplots(figsize=(14, 7))
    # Conditional bar coloring: negative (underwater), zero (break-even), positive (profitable)
    neg_mask = df['margin_threshold'] < 0
    pos_mask = df['margin_threshold'] > 0
    zero_mask = df['margin_threshold'] == 0

    # Negative margins (underwater) - muted red
    ax1.bar(
        df['quantile'][neg_mask], df['margin_threshold'][neg_mask],
        color='#C4302B', edgecolor='#FFFFFF', linewidth=0.5,
        width=0.9, label='Negative Margin'
    )
    # Positive margins - blue
    ax1.bar(
        df['quantile'][pos_mask], df['margin_threshold'][pos_mask],
        color='#1F77B4', edgecolor='#FFFFFF', linewidth=0.5,
        width=0.9, label='Positive Margin'
    )
    # Zero margins (if any) - neutral gray (small group, optional legend)
    if zero_mask.any():
        ax1.bar(
            df['quantile'][zero_mask], df['margin_threshold'][zero_mask],
            color='#B0B0B0', edgecolor='#FFFFFF', linewidth=0.5,
            width=0.9, label='Zero Margin'
        )
    ax1.set_xlabel('Quantile (%)')
    ax1.set_ylabel('Margin Threshold (USD)')
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.2f}'))

    ax2 = ax1.twinx()
    # Plot cumulative margin with color by sign: green for positive, red for negative
    cum = df['cumulative_margin']
    q = df['quantile']
    pos_vals = cum.where(cum >= 0, np.nan)
    neg_vals = cum.where(cum < 0, np.nan)
    # Positive cumulative: solid green, thicker
    ax2.plot(
        q, pos_vals,
        color='#2CA02C', linewidth=2.8, linestyle='-', label='Cumulative (positive)'
    )
    # Negative cumulative: dashed red, slightly thinner
    ax2.plot(
        q, neg_vals,
        color='#C4302B', linewidth=1.8, linestyle='--', label='Cumulative (negative)'
    )
    # Mark sign-change points to draw attention
    try:
        arr = cum.to_numpy()
        signs = np.sign(arr)
        change_idx = np.where(np.diff(signs) != 0)[0] + 1
        if change_idx.size > 0:
            ax2.scatter(q.iloc[change_idx], arr[change_idx], color='#444444', s=32, zorder=7, label='_nolegend_')
    except Exception:
        # fallback: ignore marker plotting on unexpected types
        pass
    ax2.set_ylabel('Cumulative Margin (USD)')
    ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))

    # Break-even line (cumulative = 0) and shaded underwater region
    ax2.axhline(0, color='#444444', linewidth=1.1, linestyle='-', alpha=0.85, label='_nolegend_')
    try:
        mask_underwater = (df['cumulative_margin'] < 0).tolist()
        ax2.fill_between(
            df['quantile'], df['cumulative_margin'], 0,
            where=mask_underwater,
            color='#B30000', alpha=0.12, interpolate=True, label='_nolegend_'
        )
        # Add label inside shaded region anchored to the median underwater quantile
        min_cum = float(df['cumulative_margin'].min())
        underwater_idx = np.where(df['cumulative_margin'].to_numpy() < 0)[0]
        if underwater_idx.size > 0 and min_cum < 0:
            # median underwater quantile for robust placement
            med_q = float(df['quantile'].iloc[underwater_idx].median())
            med_cum = float(np.median(df['cumulative_margin'].to_numpy()[underwater_idx]))
            text_x = med_q
            text_y = med_cum * 0.6
            ax2.text(
                text_x, text_y, 'Cumulative Underwater\nExperience',
                color='#7F0000', fontsize=11, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.35', fc='white', ec='#B30000', alpha=0.85)
            )
    except Exception:
        # Gracefully ignore shading issues (e.g., all values positive or type conversion edge cases)
        pass

    ax1.axhline(mean_val, color='#FFA600', linestyle='--', linewidth=1.3, label=f"Mean: ${mean_val:,.2f}")
    ax1.axhline(median_val, color='#2CA02C', linestyle='--', linewidth=1.3, label=f"Median: ${median_val:,.2f}")

    first_profitable_idx = next((i for i, v in enumerate(df['margin_threshold']) if v > 0), None)
    first_positive_cum_idx = next((i for i, v in enumerate(df['cumulative_margin']) if v > 0), None)

    if first_profitable_idx is not None:
        q = df['quantile'][first_profitable_idx]
        val = df['margin_threshold'][first_profitable_idx]
        ax1.scatter([q], [val], color='#000000', zorder=5, s=35)
        ax1.annotate(
            f"First profitable\nQ{q}: ${val:,.2f}",
            xy=(q, val), xytext=(q + (max_quantile-min_quantile)*0.03, val*1.15 if val != 0 else 1 or 1),
            arrowprops=dict(arrowstyle='->', color='#333333', lw=1),
            fontsize=10, bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#666666', alpha=0.9)
        )

    if first_positive_cum_idx is not None:
        q2 = df['quantile'][first_positive_cum_idx]
        val2 = df['cumulative_margin'][first_positive_cum_idx]
        ax2.scatter([q2], [val2], color='#8B0000', zorder=6, s=40)
        ax2.annotate(
            f"Break-even cumulative\nQ{q2}: ${val2:,.0f}",
            xy=(q2, val2), xytext=(q2 + (max_quantile-min_quantile)*0.04, val2*1.05 if val2 != 0 else 1 or 1),
            arrowprops=dict(arrowstyle='->', color='#8B0000', lw=1),
            fontsize=10, bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#8B0000', alpha=0.9)
        )

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    all_handles = list(handles1) + list(handles2)
    all_labels = list(labels1) + list(labels2)
    # Filter and deduplicate desired legend entries
    keep = ('Negative Margin', 'Positive Margin', 'Zero Margin', f"Mean: ${mean_val:,.2f}", f"Median: ${median_val:,.2f}", 'Cumulative (positive)', 'Cumulative (negative)')
    legend_items = []
    seen = set()
    for h, lab in zip(all_handles, all_labels):
        if lab in keep and lab not in seen and not lab.startswith('_'):
            legend_items.append((h, lab))
            seen.add(lab)
    legend = None
    if legend_items:
        legend = ax1.legend([h for h, _ in legend_items], [lab for _, lab in legend_items], frameon=True, loc='upper left')
    if legend is not None:
        legend.get_frame().set_alpha(0.85)
        legend.get_frame().set_edgecolor('#CCCCCC')

    ax1.set_title('Margin Over NADAC Distribution & Cumulative Profitability', pad=18)
    ax1.grid(axis='y', linestyle=':', alpha=0.55)

    # Consistent, readable quantile spacing
    span = max_quantile - min_quantile
    candidate_intervals = [1, 2, 5, 10, 20]
    interval = candidate_intervals[-1]
    for iv in candidate_intervals:
        if span / iv <= 15:  # target maximum number of tick labels
            interval = iv
            break
    ticks = list(range(min_quantile, max_quantile + 1, interval))
    if ticks[-1] != max_quantile:
        ticks.append(max_quantile)
    ax1.set_xticks(ticks)
    ax1.set_xlim(min_quantile - 0.5, max_quantile + 0.5)

    for spine in ['top', 'right']:
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)

    fig.tight_layout()
    output.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)
    return output
