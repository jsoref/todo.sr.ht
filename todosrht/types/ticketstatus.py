from enum import IntFlag, Enum

class TicketStatus(IntFlag):
    reported = 0
    confirmed = 1
    in_progress = 2
    pending = 4
    resolved = 8

class TicketResolution(IntFlag):
    unresolved = 0
    fixed = 1
    implemented = 2
    wont_fix = 4
    by_design = 8
    invalid = 16
    duplicate = 32
    not_our_bug = 64
    closed = 128

class TicketAuthenticity(Enum):
    authentic = 0
    unauthenticated = 1
    tampered = 2
