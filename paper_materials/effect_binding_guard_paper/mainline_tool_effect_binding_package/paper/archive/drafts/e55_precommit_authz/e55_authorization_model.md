# E55 Authorization Model

E55 models pre-commit mediation as explicit authorization checking over effect-resource-operation atoms.

The deployable guard path receives only visible tool schema/arguments, task authorization context, non-oracle evidence summaries, and provenance/control-source metadata. It recomputes atoms from the visible call and checks whether every affected recipient, attendee, file, channel, account, visibility, operation mode, and provenance source is covered by the task authorization.

Default policy: all atoms must be authorized. Unknown canonicalization or insufficient evidence causes `ABSTAIN`; hard provenance violations cause `DENY`.
