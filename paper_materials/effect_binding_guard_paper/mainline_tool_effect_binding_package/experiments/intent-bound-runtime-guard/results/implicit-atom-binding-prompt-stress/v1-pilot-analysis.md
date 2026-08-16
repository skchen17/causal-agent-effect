# Implicit Sub-Effect V1 Pilot

V1 tested eight metadata-only clean/injected pairs without explicit injection
markers. The full no-guard diagnostic produced clean utility `6/8`, injected
utility `7/8`, and attack success `0/8`.

This means V1 did not create a discriminating attack condition. It cannot
support a claim that any defense, atom representation, or prompt prevented an
attack. The result is retained as a negative design pilot.

V2 was defined after observing this lack of signal. It retains the same tasks,
axes, and scoring sidecar but presents the clean/mutated value in a matched
schema-shaped `resolved_tool_arguments` view. V2 is evaluated separately and
must not be described as pre-registered before the V1 diagnostic.
