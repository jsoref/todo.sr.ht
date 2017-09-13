from enum import IntFlag

class TicketStatus(IntFlag):
    reported = 0
    confirmed = 1
    in_progress = 2
    pending = 4
    resolved = 8
    shipped = 16

class TicketResolution(IntFlag):
    unresolved = 0
    fixed = 1
    implemented = 2
    wont_fix = 4
    by_design = 8
    invalid = 16
    duplicate = 32
