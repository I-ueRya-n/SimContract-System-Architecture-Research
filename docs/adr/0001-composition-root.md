# ADR 0001: Composition root for domain wiring

The engine must remain ignorant of concrete domains (spec section 4). The registry
accepts alias -> adapter factory registrations. simcontract/composition.py is the
single module allowed to import both engine and concrete domain packages; only entry
points (CLI, experiments) import it.
