This module integrates Budget Control with Petty Cash.

When an expense is paid by petty cash, the clearing entry is posted on the
petty cash holder's account. The expense side already commits the budget, so
the destination (clearing) line of the petty cash entry must not affect the
budget again.

To prevent the double commit, this module marks the petty cash clearing
line with `not_affect_budget = True`.
