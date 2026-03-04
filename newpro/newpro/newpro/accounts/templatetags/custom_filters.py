from django import template

register = template.Library()

@register.filter
def get_item_classroom(timetable, classroom):
    return timetable.filter(classroom=classroom)

@register.filter
def get_item_faculty(timetable, faculty):
    return timetable.filter(faculty=faculty)

@register.filter
def get_item_day(entries, day):
    return {entry.time_slot.period: entry for entry in entries.filter(time_slot__day=day)}

@register.filter
def get_item_period(day_entries, period):
    return day_entries.get(period)
