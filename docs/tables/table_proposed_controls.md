| Scenario | Reviewed | Archived | Coverage | Conflict-hit rate | vs random |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Shipped: no review | 0.0 | 0.0 | 0.0 | — | — |
| Shipped: recency | 41.3 | 0.0 | 0.0 | 0.0 | -38.5 pt |
| Shipped: importance | 41.0 | 17.8 | 44.6 | 43.5 | +5.0 pt |
| Shipped: decay | 41.5 | 21.0 | 52.5 | 50.6 | +12.1 pt |
| Proposed: random (E1) | 41.0 | 15.4 | 38.5 | 37.6 | -0.9 pt |
| Proposed: recency, 25% late writes (E2) | 41.2 | 9.3 | 23.3 | 22.7 | -15.8 pt |
| Proposed: recency, 50% late writes (E2) | 41.2 | 19.1 | 47.7 | 46.4 | +7.9 pt |
| Proposed: importance, signal 0.00 (E3) | 41.2 | 14.8 | 37.1 | 36.0 | -2.5 pt |
| Proposed: importance, signal 0.25 (E3) | 41.2 | 28.3 | 70.8 | 68.7 | +30.2 pt |
| Proposed: importance, signal 0.50 (E3) | 41.0 | 31.9 | 79.8 | 77.8 | +39.4 pt |
| Proposed: importance, signal 0.75 (E3) | 41.0 | 35.0 | 87.5 | 85.4 | +46.9 pt |
| Proposed: importance, signal 1.00 (E3) | 41.0 | 38.3 | 95.8 | 93.5 | +55.0 pt |

Every number above is computed from the review design alone; no model is called, because archiving is deterministic. The `random` row is the baseline the paper lacks, and its theoretical hit rate is 38.5% (40 superseded records among 104). The last five rows separate an importance *policy* from an importance *signal*: coverage rises with the correlation between importance and supersession, which is the only channel through which importance can help.
