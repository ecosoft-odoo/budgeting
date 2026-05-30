To use this module, you need to:

#. Make sure the operation type and the budget period are configured (see
   *Configuration*) and that the budget control sheet of the analytic account is
   in *Controlled* status.
#. Create an outgoing transfer (delivery) whose stock moves carry an analytic
   distribution.
#. Confirm the transfer. For each analytic account, a budget commitment is
   created from the configured price source (move unit price or lot standard
   price). If the budget is not sufficient and the period blocks over-budget
   transactions, confirmation is refused.
#. Review the committed amount on the *Budget Commitment* tab of the transfer,
   on the budget control sheet (`Stock` column) or on the budget monitoring
   report.
#. Validate the transfer. The stock journal entry is posted and recorded as
   budget *actual*, and the matching stock commitment is released, so
   consumption moves from *commitment* to *actual*.

Cancelling, reverting to draft or returning the transfer removes the related
commitment.
