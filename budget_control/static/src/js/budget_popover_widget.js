odoo.define("budget_control.budget_popover_widget", function (require) {
    "use strict";

    var AbstractField = require("web.AbstractField");
    var core = require("web.core");
    var QWeb = core.qweb;
    var fieldRegistry = require("web.field_registry");

    /**
     * Popover for a JSON field (char). Same contract as stock's popover_widget,
     * reimplemented here so the budgeting modules do not have to depend on
     * `stock` just to render an info popover.
     * {
     *  'msg': '<CONTENT OF THE POPOVER>',
     *  'icon': '<FONT AWESOME CLASS>' (optional),
     *  'color': '<COLOR CLASS OF ICON>' (optional),
     *  'title': '<TITLE OF POPOVER>' (optional),
     *  'popoverTemplate': '<QWEB TEMPLATE NAME>' (optional)
     * }
     */
    var BudgetPopoverWidgetField = AbstractField.extend({
        supportedFieldTypes: ["char"],
        buttonTemplate: "budget_control.popoverButton",
        popoverTemplate: "budget_control.popoverContent",
        trigger: "focus",
        placement: "top",
        html: true,
        color: "text-primary",
        icon: "fa-info-circle",

        _render: function () {
            // Guard the empty string too: an unset char field must not throw here.
            var value = this.value ? JSON.parse(this.value) : false;
            if (!value) {
                this.$el.html("");
                return;
            }
            this.$el.css("max-width", "17px");
            this.$el.html(
                QWeb.render(
                    this.buttonTemplate,
                    _.defaults(value, {
                        color: this.color,
                        icon: this.icon,
                    })
                )
            );
            this.$el.addClass("o_widget");
            this.$el.find("a").prop("special_click", true);
            this.$popover = $(
                QWeb.render(value.popoverTemplate || this.popoverTemplate, value)
            );
            this.$el.find("a").popover({
                content: this.$popover,
                html: this.html,
                placement: this.placement,
                title: value.title || this.title.toString(),
                trigger: this.trigger,
                delay: {show: 0, hide: 100},
            });
        },

        destroy: function () {
            this.$el.find("a").popover("dispose");
            this._super.apply(this, arguments);
        },
    });

    fieldRegistry.add("budget_popover_widget", BudgetPopoverWidgetField);

    return BudgetPopoverWidgetField;
});
