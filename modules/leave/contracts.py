"""leave's public surface. Plural by signature — an N+1 is unwritable.

Empty until another module needs a read from leave. Nothing here mutates; a
change another module needs is an event, not a setter.
"""
