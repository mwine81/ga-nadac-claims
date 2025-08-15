from analysis import get_margin_stats
import polars as pl
from polars import col as c
from config import FIGURE_DIR
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
from pathlib import Path
from figures.plotting_prep import prepare_quantile_distribution
import pandas as pd
from tables import load_base_table
from expressions import median_quantity, unit_margin, extract_pbm
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from analysis import starndard_margin_analysis

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


def plot_standardized_margin_grouped(
    product: str = 'Buprenorphine HCl-Naloxone HCl Sublingual Tablet Sublingual 8-2 MG',
    monthly: bool = True,
    output: Path | None = None,
) -> Path:
    """Create a grouped-bar chart comparing median vs mean standardized prescription margin by DOS (year-month).

    - `monthly`: if True, resample to month-end and aggregate margins (median/mean) and rx_count.
    Returns the saved Path.
    """

    base = (load_base_table()
        .filter(c.product == product)
    )
    median_qty = base.select(median_quantity()).collect(engine='streaming').item()
    # import the analysis LF function
    lf = starndard_margin_analysis(product=product)
    df = lf.collect(engine='streaming').to_pandas()

    if df.empty:
        raise ValueError('starndard_margin_analysis returned no rows for the requested product')

    # Ensure dos is datetime and use month-end grouping if requested
    if 'dos' in df.columns:
        df['dos'] = pd.to_datetime(df['dos'])
        df = df.set_index('dos')
    else:
        df.index = pd.to_datetime(df.index)

    if monthly:
        df = df.resample('ME').agg({
            'median_standardized_margin': 'median',
            'mean_standardized_margin': 'mean',
            'rx_count': 'sum',
        })

    # Prepare labels and values (robust to index types)
    try:
        labels = df.index.to_period('M').astype(str).tolist() # type: ignore
    except Exception:
        labels = [pd.to_datetime(idx).strftime('%Y-%m') for idx in df.index]

    med = df['median_standardized_margin'].to_numpy()
    mean = df['mean_standardized_margin'].to_numpy()

    x = np.arange(len(labels))
    # narrower bars + more spacing
    width = 0.32

    # Wider figure scaled to number of labels but with a larger minimum width
    # increase scaling to give more horizontal room for month labels
    fig_w = max(14, len(labels) * 0.8)
    # increase height to give extra vertical room for labels/rotated text
    fig, ax = plt.subplots(figsize=(fig_w, 8))

    # Colors and styling: blue (median) and orange (mean), hatch for mean for print readability
    median_color = '#1F77B4'
    mean_color = '#FF7F0E'
    median_edge = '#0b3d91'
    mean_edge = '#b35000'

    med_bars = ax.bar(x - width/2, med, width, label='Median Margin Over NADAC', color=median_color, edgecolor=median_edge, linewidth=1.0)
    mean_bars = ax.bar(x + width/2, mean, width, label='Mean Margin Over NADAC', color=mean_color, edgecolor=mean_edge, linewidth=1.0, hatch='///')

    # Connector line for mean to help track trend across months
    ax.plot(x + width/2, mean, marker='o', color=mean_edge, linewidth=1.2, linestyle='--', alpha=0.95)

    ax.set_ylabel('Standardized Margin Over NADAC (USD)')
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.2f}'))

    # Dynamic x-tick thinning for long ranges
    max_ticks = 14
    if len(labels) > max_ticks:
        step = int(np.ceil(len(labels) / max_ticks))
        ticks = x[::step]
        tick_labels = [labels[i] for i in range(0, len(labels), step)]
    else:
        ticks = x
        tick_labels = labels

    ax.set_xticks(ticks)
    # Rotate slightly and move labels below the axis; add bottom margin so labels don't overlap the plot
    ax.set_xticklabels(tick_labels, rotation=30, ha='right')
    fig.subplots_adjust(bottom=0.20)
    ax.xaxis.set_tick_params(pad=6)
    # two-line title: short description and product (with median qty) on second line
    ax.set_title(f'Standardized Prescription Margin (Mean vs Median)\n{product} x {median_qty}', pad=18)

    # USD data labels: prefer matplotlib.bar_label for robustness
    def _usd(v):
        return f'${v:,.2f}'

    # ensure y-limits leave room for rotated labels so they are not clipped
    combined_min = float(min(np.nanmin(med) if med.size else 0, np.nanmin(mean) if mean.size else 0))
    combined_max = float(max(np.nanmax(med) if med.size else 0, np.nanmax(mean) if mean.size else 0))
    yrange = combined_max - combined_min
    if yrange == 0:
        pad = abs(combined_max) * 0.1 if combined_max != 0 else 1.0
    else:
        pad = yrange * 0.12
    ax.set_ylim(combined_min - pad, combined_max + pad)

    # label sparsity: choose a step so we show ~max 14 labels
    max_labels = 14
    label_step = max(1, int(np.ceil(len(x) / max_labels)))

    try:

        # build labels but leave blanks for skipped positions to reduce clutter
        labels_med = [_usd(v) if (i % label_step == 0) else '' for i, v in enumerate(med)]
        labels_mean = [_usd(v) if (i % label_step == 0) else '' for i, v in enumerate(mean)]

        # color negatives red, positives dark; bar_label accepts a color list
        labels_med_colors = ['red' if (v < 0 and (i % label_step == 0)) else 'black' for i, v in enumerate(med)]
        labels_mean_colors = ['red' if (v < 0 and (i % label_step == 0)) else 'black' for i, v in enumerate(mean)]

        # increase padding so labels sit a little away from bar ends
        ax.bar_label(med_bars, labels=labels_med, padding=6, rotation=90, color=labels_med_colors, fontsize=8)
        ax.bar_label(mean_bars, labels=labels_mean, padding=6, rotation=90, color=labels_mean_colors, fontsize=8)
    except Exception:
        # Fallback: draw text manually (keeps previous behavior)
        y_offset = max(abs(med).max(), abs(mean).max()) * 0.035 if len(x) > 0 else 0.1
        # fallback: label every label_step-th bar
        for i in range(len(x)):
            if i % label_step != 0:
                continue
            # median label (left bar of the group)
            y_med = med[i]
            if y_med >= 0:
                va_med = 'bottom'
                y_med_pos = y_med + y_offset
            else:
                va_med = 'top'
                y_med_pos = y_med - y_offset
            med_color = 'red' if y_med < 0 else 'black'
            ax.text(
                x[i] - width/2, y_med_pos, _usd(y_med), ha='center', va=va_med, rotation=90,
                fontsize=9, color=med_color, clip_on=False, zorder=10,
                bbox=dict(facecolor='white', edgecolor='none', pad=0.3, alpha=0.9)
            )

            # mean label (right bar of the group)
            y_mean = mean[i]
            if y_mean >= 0:
                va_mean = 'bottom'
                y_mean_pos = y_mean + y_offset
            else:
                va_mean = 'top'
                y_mean_pos = y_mean - y_offset
            mean_color = 'red' if y_mean < 0 else 'black'
            ax.text(
                x[i] + width/2, y_mean_pos, _usd(y_mean), ha='center', va=va_mean, rotation=90,
                fontsize=9, color=mean_color, clip_on=False, zorder=10,
                bbox=dict(facecolor='white', edgecolor='none', pad=0.3, alpha=0.9)
            )

    # Float the legend inside the axes at upper-left so the chart can use full figure width
    ax.legend(frameon=True, loc='upper left', bbox_to_anchor=(0.02, 0.98), bbox_transform=ax.transAxes)
    fig.tight_layout()

    FIGURE_DIR.mkdir(exist_ok=True, parents=True)
    if output is None:
        safe_name = product[:40].replace(' ', '_').replace('/', '_')
        output = FIGURE_DIR / f'standardized_margin_grouped_{safe_name}.png'
    output.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(output, dpi=300)
    plt.close(fig)
    return output




def box_margin_plot(
       product: str = 'Buprenorphine HCl-Naloxone HCl Sublingual Tablet Sublingual 8-2 MG'
):
    
    base = (load_base_table()
        .filter(c.product == product)
    )
    
    median_qty = base.select(median_quantity()).collect(engine='streaming').item()

    data = (
    base
    .with_columns(extract_pbm())
    .with_columns((unit_margin() * median_qty).alias('margin_over_nadac'))
    .collect(engine='streaming')
    )

    # improved boxplot: order by median, hide extreme fliers, overlay jittered points,
    # show mean markers, annotate sample size, format y-axis as USD and save figure
    sns.set_theme(style='whitegrid', rc={'grid.linewidth': 0.5})
    fig, ax = plt.subplots(figsize=(14, 8))

    # convert to pandas and order PBMs by median margin for clearer comparison
    df = data.to_pandas()
    if df.empty:
        raise ValueError('No data to plot for PBM boxplot')
    order = df.groupby('pbm')['margin_over_nadac'].median().sort_values().index

    # boxplot without extreme outliers and a light palette
    sns.boxplot(data=df, x='pbm', y='margin_over_nadac', order=order,
                showfliers=False, palette='Set2', ax=ax, linewidth=1.0)

    # overlay jittered individual points so density is visible, color negatives red
    # manual jitter + scatter so we can color negative margins differently
    rng = np.random.default_rng(1)
        # reduce jitter so points stay closer to the box center
    jitter_scale = 0.3
    for i, pbm in enumerate(order):
        sub = df[df['pbm'] == pbm]
        if sub.empty:
            continue
        n = len(sub)
        # use uniform jitter in a tight band so points remain within the box width
        jitter = rng.uniform(-jitter_scale, jitter_scale, size=n)
        xs = np.full(n, i) + jitter
        ys = sub['margin_over_nadac'].values
        neg_mask = ys < 0
        # positives: muted black/gray
        # positives: smaller, moderately opaque
        if (~neg_mask).any():
            ax.scatter(xs[~neg_mask], ys[~neg_mask], color='0.2', s=4, alpha=0.1, zorder=5)
        # negatives: red shade
        # negatives: slightly larger and more opaque to emphasize
        if neg_mask.any():
            ax.scatter(xs[neg_mask], ys[neg_mask], color='#d73027', s=4, alpha=0.1, zorder=6)

    # draw mean as a white diamond with black edge
    means = df.groupby('pbm')['margin_over_nadac'].mean()
    for i, pbm in enumerate(order):
        ax.scatter(i, means.loc[pbm], marker='D', s=60, facecolor='white', edgecolor='black', zorder=10)

    # annotate sample size above each box
    counts = df['pbm'].value_counts().reindex(order)
    ylim_top = ax.get_ylim()[1]
    for i, (pbm, n) in enumerate(counts.items()):
        ax.text(i, ylim_top - (ylim_top * 0.02), f'n={n}', ha='center', va='top', fontsize=8, rotation=0)

    # money formatting on y-axis
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))

    plt.xticks(rotation=30, ha='right')
    ax.set_ylabel('Standardized Margin over NADAC (USD)')
    ax.set_xlabel('PBM')
    plt.title(f'Standardized Margin over NADAC by PBM\n{product} x {median_qty}\n (January 2024 - March 2025)', pad=14)

    # save high-res copy
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURE_DIR / 'boxplot_margin_over_nadac_by_pbm.png'
    plt.tight_layout()
    plt.savefig(out, dpi=300)
    print(out)



if __name__ == "__main__":
    # Example usage
    plot_standardized_margin_grouped()