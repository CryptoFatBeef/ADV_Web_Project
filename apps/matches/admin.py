from django.contrib import admin
from django.db.models import Count

from .models import KPNPDevice, MatchEntry, Tournament


class MatchEntryInline(admin.TabularInline):
    model  = MatchEntry
    extra  = 1
    fields = (
        'member', 'belt_at_match', 'weight_class',
        'result', 'medal', 'placement', 'score', 'opponent_name',
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # lock belt_at_match once Tournament is saved
            return ['belt_at_match']
        return []


class KPNPDeviceInline(admin.TabularInline):
    model  = KPNPDevice
    extra  = 0
    fields = ('device_type', 'serial_number', 'notes')


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    inlines         = [MatchEntryInline, KPNPDeviceInline]
    list_display    = ('name', 'match_type', 'event', 'is_international', 'organised_by', 'entry_count')
    list_filter     = ('match_type', 'is_international')
    search_fields   = ('name', 'organised_by', 'location')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event').annotate(
            _entry_count=Count('entries')
        )

    @admin.display(description='Entries', ordering='_entry_count')
    def entry_count(self, obj):
        return obj._entry_count


@admin.register(MatchEntry)
class MatchEntryAdmin(admin.ModelAdmin):
    list_display    = ('member', 'tournament', 'belt_at_match', 'weight_class', 'result', 'medal', 'placement')
    list_filter     = ('result', 'medal', 'weight_class', 'tournament__match_type')
    search_fields   = ('member__member_id', 'member__user__last_name', 'tournament__name')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('member__user', 'tournament')
