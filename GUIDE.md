# Build a qualified experiment readout

Use disjoint cohorts from a binary-outcome experiment. For each cohort, enter exposed and converted people in the control and treatment arms, keeping each person in one arm and counting their conversion at most once. Record whether the observation window has closed. Provide the planned treatment share, randomized assignment status and a minimum reporting size for each arm.

The tool reports treatment minus control in percentage points, a nominal 95% Newcombe score interval using separate Wilson bounds, and relative lift where the control rate is positive. Zero exposures suppress the numeric comparison. Validity checks flag incomplete windows, small arms and nonrandom assignment. When expected counts permit, an allocation imbalance larger than three expected standard deviations is flagged for investigation. That screen is not a complete randomization audit.

Approve cohorts to produce a Markdown readout with arm counts, interval, review notes and all validity flags. Approval never clears a warning. The estimates assume independent Bernoulli observations, and they have no correction for multiple comparisons, sequential monitoring or clustered assignment. Cohort-specific differences and validity checks should be interpreted before any product decision.
