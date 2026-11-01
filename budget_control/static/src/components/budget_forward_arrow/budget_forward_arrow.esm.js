import {Component, useProps} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";

/**
 * Arrow between where a forward line comes from and where it goes,
 * highlighted when the line is carried elsewhere than by default
 * (forward_changed).
 */
export class BudgetForwardArrow extends Component {
    static template = "budget_control.BudgetForwardArrow";
    props = useProps(standardWidgetProps);
}

registry
    .category("view_widgets")
    .add("budget_forward_arrow", {component: BudgetForwardArrow});
