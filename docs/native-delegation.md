# Relayhelm native delegation

Before every `delegate_task` spawn, Relayhelm presents **Keep one agent** and
**Split task** through the host's interactive question callback. The question
lists the child goals and the resolved model. Only the explicit Split task
answer authorizes that batch; model-supplied consent flags, silence, missing
callbacks and callback failures do not. Listing, steering and stopping existing
children do not prompt. Nested orchestrators forward the host callback and ask
again for their own proposed children. Hosts without interactive questions keep
working as a single agent.

Children inherit the parent's selected model unless the user configured
`delegation.model` / `delegation.provider`. They inherit reasoning settings unless
`delegation.reasoning_effort` explicitly overrides them. No child inherits the
parent's fallback model chain. Same-provider credential rotation remains
available. If construction resolves a different model, Relayhelm closes the
child and refuses the spawn.

Each child receives its goal, supplied task context, output contract and project
workspace. Child sessions stay separate and skip automatic memory preload.
This is not a byte-for-byte copy of the parent conversation: callers must include
all decisions, constraints and files needed by that child. Context Broker's
immutable model handoffs are the separate mechanism for transferring a saved
checkpoint. Relayhelm cannot guarantee a model's answer quality; the parent
must review and verify child output before accepting an integrated change.

A child completes only when its terminal result explicitly reports completion,
contains usable output, and passes any declared output schema. Provider errors,
failed retries and exhausted iteration budgets remain failures with
`completed: false` and `failure_reason`; partial summaries remain available.
Interrupted children remain interrupted. Tool-call traces and schema outcomes
are retained as review evidence, but a child's completion flag alone does not
prove that tests passed or that a requested change was integrated.
