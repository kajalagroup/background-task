from django.contrib import admin
from django.contrib.auth import (
    get_user_model
)
from django.utils.translation import gettext as _
from kbackgroundtask.models import (
    BackgroundTask,
)
from jutil.admin import ModelAdminBase
from django.contrib.admin import SimpleListFilter
from django.utils.timezone import now
from datetime import timedelta
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from jutil.format import format_timedelta
from django.http import HttpRequest
from django.core.management import call_command
from django.contrib.messages import add_message
from django.core.checks import messages
from django.shortcuts import redirect

User = get_user_model()


class BackgroundTaskStateFilter(SimpleListFilter):
    title = _("state")
    parameter_name = "state"

    def lookups(self, request, model_admin):
        opts = [
            ("0", _("ok")),
            ("1", _("non-completed")),
            ("2-1", _("not executed over 24 hours")),
            ("2-7", _("not executed over 7 days")),
            ("2-31", _("not executed over 31 days")),
        ]
        for obj in list(BackgroundTask.objects.all().distinct("signal")):
            assert isinstance(obj, BackgroundTask)
            opts.append((obj.signal, _(obj.signal)))
        return opts

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            if val == "0":
                return queryset.exclude(signal="error")
            if val == "1":
                return queryset.filter(
                    signal__in=BackgroundTask.UNFINISHED_TASK_SIGNALS
                )
            if val.startswith("2-"):
                days = int(val.split("-")[1])
                active_tasks = list(
                    BackgroundTask.objects.filter(
                        created__gt=now() - timedelta(days=days)
                    )
                    .distinct("name")
                    .values_list("name", flat=True)
                )
                return queryset.exclude(name__in=active_tasks)
            return queryset.filter(signal=val)
        return queryset


class BackgroundTaskAdmin(ModelAdminBase):
    actions = ()
    date_hierarchy = "created"
    list_filter = (
        BackgroundTaskStateFilter,
        "name",
    )
    search_fields = ("=task_id",)
    list_display = (
        "id",
        "created",
        "signal_localized",
        "name_link",
        "admin_runtime",
        "admin_error_brief",
    )
    fields = (
        "id",
        "name",
        "task_id",
        "created",
        "last_modified",
        "signal_localized",
        "complete",
        "executing",
        "locked",
        "retrying",
        "scheduled",
        "canceled",
        "revoked",
        "failed",
        "error",
        "admin_runtime",
    )
    readonly_fields = fields

    def admin_error_brief(self, obj):
        assert isinstance(obj, BackgroundTask)
        err = obj.error_brief
        font_color = "green" if obj.is_newer_ok() else "red"
        return format_html('<span style="color:{}">{}</span>', font_color, err)

    admin_error_brief.short_description = _("error")  # type: ignore

    def signal_localized(self, obj) -> str:
        assert isinstance(obj, BackgroundTask)
        return _(obj.signal)

    signal_localized.short_description = _("signal")  # type: ignore
    signal_localized.admin_order_field = "signal"  # type: ignore

    def admin_runtime(self, obj):
        assert isinstance(obj, BackgroundTask)
        dt = obj.runtime
        if dt is not None:
            return format_timedelta(dt) or "<1s"
        return ""

    admin_runtime.short_description = _("runtime")  # type: ignore

    def name_link(self, obj):
        assert isinstance(obj, BackgroundTask)
        return mark_safe(
            f"<a href='/admin/backgroundtask/backgroundtask/?name={obj.name}'>{obj.name}</a>"
        )

    name_link.short_description = _("name")  # type: ignore
    name_link.admin_order_field = "name"  # type: ignore

    def task_link(self, obj):
        assert isinstance(obj, BackgroundTask)
        return mark_safe(
            f"<a href='/admin/backgroundtask/backgroundtask/?q={obj.task_id}'>{obj.task_id}</a>"
        )

    task_link.short_description = _("task")  # type: ignore
    task_link.admin_order_field = "task_id"  # type: ignore

    def changelist_view(self, request: HttpRequest, extra_context=None):
        if request.GET.get("flush-redis", "") == "1":
            call_command("redis_flushdb", force=True)
            add_message(request, messages.INFO, "Background task Redis locks flushed")
            return redirect(request.META["HTTP_REFERER"])
        if request.GET.get("reset-error-if-newer-ok", "") == "1":
            for bt in list(BackgroundTask.objects.filter_unfinished()):
                assert isinstance(bt, BackgroundTask)
                if bt.is_newer_ok():
                    add_message(request, messages.INFO, f"{bt} deleted")
                    bt.delete()
            add_message(
                request,
                messages.INFO,
                "Errors reset for tasks which have newer complete runs",
            )
            return redirect(request.META["HTTP_REFERER"])
        return super().changelist_view(request, extra_context)


admin.site.register(BackgroundTask, BackgroundTaskAdmin)
