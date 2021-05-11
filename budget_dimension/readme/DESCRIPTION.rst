This is base module to add tag dimensions to budget moves, initially, to account.budget.move.
The additional dimension is many2one field of the reference model of the DIMENSION and
will have naming as, x_m2o_DIMENSION.
Additional dimensions can result in better report analysis, budget constraints and etc.

This module can be extended for other budget moves models, with following modules,

* budget_dimension_purchase
* budget_dimension_purchase_request
* budget_dimension_expense
* budget_dimension_advance


**IMPORTANT**

This module extend analytic_tag_dimension_enhanced, and as such, the new dimension fields are created
when new dimension master data is created. Please make sure, new dimension is setup only after all
required modules above was installed.
