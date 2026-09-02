# Cash Flow Break-Even and Actual-Sales Update

The Cash Flow portal now uses an automatic planning policy:

- Every historical actual positive-sales day is included in the average.
- Blank/no-sale days are excluded from the averaging sample.
- Actual recorded sales always override the projection.
- A prior manual amount, including ₱5,000, is not used.
- Blank days use the higher of the lifetime actual-sales average or the filtered monthly break-even sales requirement.
- Break-even sales are calculated from included scheduled expenses less included additional income, divided by the 40% contribution margin produced by the existing 60% COGS rule.
- COGS remains automatically calculated at 60% of actual or projected sales.
- Macleen's existing project rule that Vault Drops are included in sales is unchanged.

Analysis exclusions do not delete source records. The portal excludes:

- expenses matching Tet, Joy, Delro, Motorcycle, Kevin, or Investor; and
- income or completed-sale records matching “Sample work.”

The portal displays an exclusion audit so Admin can confirm what was left out.
