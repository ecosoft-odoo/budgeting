import {Component, computed, t, useProps} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {usePopover} from "@web/core/popover/popover_hook";

export class BudgetPopover extends Component {
    static template = "budget_control.BudgetPopover";
    props = useProps({
        title: t.string().optional(),
        analytic: t.array().optional([]),
        close: t.function().optional(),
    });
}

/**
 * Budget figures of the analytic accounts of a document line, read from a
 * JSON char field: {"title": "...", "analytic": [{id, name, budget,
 * consumed, balance}, ...]}.
 */
export class BudgetPopoverField extends Component {
    static template = "budget_control.BudgetPopoverField";
    props = useProps(standardFieldProps);

    jsonValue = computed(() =>
        JSON.parse(this.props.record.data[this.props.name] || "{}")
    );

    setup() {
        this.popover = usePopover(BudgetPopover, {position: "top"});
    }

    showPopup(ev) {
        const {title, analytic} = this.jsonValue();
        this.popover.open(ev.currentTarget, {title, analytic: analytic || []});
    }
}

export const budgetPopoverField = {
    component: BudgetPopoverField,
    displayName: _t("Budget Figure"),
    supportedTypes: ["char"],
};

registry.category("fields").add("budget_popover", budgetPopoverField);
