# UrbanCart Term Project — Team Contributions

This project was completed by a two-person team. Work was split by
discipline: one member led the technical/analytical build, the other
led the written and presentation deliverables. Both members reviewed
and signed off on the final report, deck, and executive summary.

## [Your Name] — Coding & Visualization

- Wrote and ran the SQL extraction queries against `ecommerce.db`
  (revenue by category, top customers, month-over-month trend, return
  rate, RFM-adjacent cohort queries, product rankings, payment-method
  mix, and the custom margin-by-country query).
- Handled data cleaning and integration in code: standardizing the
  legacy customer export's mixed date formats, deduplicating customer
  records, resolving the missing-value policy, flagging price outliers,
  merging the supplier catalog, and cleaning `order_items`.
- Implemented the core analytical methods from scratch in NumPy: RFM
  segmentation, cosine-similarity product recommendations, linear
  regression via the normal equation, and the Monte Carlo stockout
  simulation — including the sanity checks against library functions
  used to verify (not produce) each result.
- Built all charts and visualizations referenced throughout the report
  (revenue seasonality, RFM segment revenue, margin by category,
  ratings vs. repeat purchase, device/country conversion, forecast with
  prediction interval, stockout risk).

## Lina — Documentation & Presentation

- Wrote and structured the full project report, including the
  executive summary, business context, findings write-ups, limitations,
  and recommendations sections.
- Translated the technical analysis and charts into plain-language
  business narrative for a non-technical audience.
- Designed and built the slide presentation summarizing the project for
  stakeholders.
- Coordinated formatting, proofreading, and final assembly of the
  report and deck.

## Shared

Both members reviewed the final numbers, findings, and recommendations
together before submission to make sure the analysis and the narrative
matched.
