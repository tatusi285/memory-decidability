| Condition | Stale (%) | Probes | 95% CI over probes | 95% CI over chains |
| :--- | ---: | ---: | ---: | ---: |
| Absolute dates, newest first | 0.2 | 1/480 | [0.0, 1.2] | [0.0, 8.8] |
| Absolute dates, oldest first | 0.0 | 0/480 | [0.0, 0.8] | [0.0, 8.8] |
| Relative notation (“day N”) | 15.8 | 76/480 | [12.7, 19.4] | [5.7, 29.8] |
| No timestamp, newest first | 100.0 | 480/480 | [99.2, 100.0] | [91.2, 100.0] |
| No timestamp, oldest first | 0.0 | 0/480 | [0.0, 0.8] | [0.0, 8.8] |

The probe interval treats each of the 480 queries as independent; the chain interval treats the 40 chains as the unit. The chain interval is the honest one, because a chain returns the same verdict at all four delays and all three seeds (see `AUDIT.md` section 3). Read the two columns together: a cell of 0.2% from one probe is compatible with anything from zero to three of the forty chains.
