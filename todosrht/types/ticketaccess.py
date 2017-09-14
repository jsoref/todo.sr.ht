from enum import IntFlag

class TicketAccess(IntFlag):
    none = 0
    browse = 1
    submit = 2
    comment = 4
    edit = 8
    triage = 16
    all = browse | submit | comment | edit | triage
