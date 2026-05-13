# IRIS radiation-channel audit

## Position

NMDB/SOPO neutron-monitor data are used as an environmental cosmic-ray variability proxy, not as individual absorbed dose, organ dose, or a direct physiological radiation-stress measurement.

## NMDB proxy summary

|   count |   mean |    std |     min |     25% |     50% |     75% |    max |
|--------:|-------:|-------:|--------:|--------:|--------:|--------:|-------:|
|     168 | 325.86 | 2.3345 | 320.249 | 323.744 | 326.666 | 327.798 | 329.58 |

## IRIS radiation proxy mapping summary

|   count |      mean |       std |   min |   25% |       50% |       75% |      max |
|--------:|----------:|----------:|------:|------:|----------:|----------:|---------:|
|     168 | 0.0730968 | 0.0306205 |  0.05 |  0.05 | 0.0511994 | 0.0984792 | 0.174823 |

## Station forcing contribution summary

| station      |   radiation_mean |   radiation_max |   radiation_std |   radiation_abs_fraction_of_total_forcing |
|:-------------|-----------------:|----------------:|----------------:|------------------------------------------:|
| Byrd         |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0734842 |
| Cape Denison |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0897511 |
| Clean Air    |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0520673 |
| Concordia    |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0436823 |
| Dome A       |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0388515 |
| Dome C       |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0491733 |
| Dome Fuji    |        0.0922462 |        0.161706 |       0.0274012 |                                 0.0415307 |

## Required manuscript correction

Radiation is retained as an environmental forcing channel only. The paper must not claim dose-response estimation or individual biological radiation injury. A sensitivity analysis should report whether removing or down-weighting this channel materially changes latent-topology results.


## Stronger phrasing

The neutron-monitor channel is used to represent time-varying polar cosmic-ray environment, analogous to an exogenous operational stressor, not to estimate absorbed dose. Its role is therefore tested through sensitivity and ablation rather than treated as a validated cardiovascular radiation pathway.
