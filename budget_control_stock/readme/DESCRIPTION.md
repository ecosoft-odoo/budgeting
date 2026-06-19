This module adds budget control on stock operations, so that goods issued
from inventory consume budget independently from the related purchase or sale
documents.

When an outgoing transfer (delivery) of an operation type with `Commit Budget`
enabled is confirmed, a ``stock.budget.move`` commitment is created per analytic
account. The committed amount is the move quantity valued at the configured price
source: the stock move's unit price (falling back to product standard price
when empty) or the lot standard price. When the
transfer is validated, the stock journal entry is posted and recorded as budget
*actual* (from the stock valuation value), while the original stock commitment is
released, so the budget consumption moves smoothly from *commitment* to *actual*.
Cancelling or reverting the transfer removes the commitment.

The committed amount can be reviewed on the *Budget Commitment* tab of the
stock transfer and on the budget monitoring report.

Open stock commitments (transfers confirmed but not yet validated at the end of
a budget period) are carried forward to the next period together with the other
commitment types of the standard *Budget Commit Forward* document.
