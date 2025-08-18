from figures.plotting import plot_price_distribution, plot_standardized_margin_grouped, box_margin_plot


if __name__ == "__main__":
    plot_price_distribution(plot_nadac=True)
    plot_standardized_margin_grouped()
    box_margin_plot()