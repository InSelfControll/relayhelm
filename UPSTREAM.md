# Upstream attribution and project separation

Relayhelm is independently maintained by InSelfControll. It was imported from
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), with
initial source revision `5ac75e91` in this checkout. The inherited Git history,
MIT license and third-party notices preserve the original authorship.

Relayhelm's repository, issue tracker and update source are
https://github.com/InSelfControll/relayhelm. Development here does not publish
changes to the upstream Hermes repository. Upstream work can be reviewed and
imported deliberately, as with any other dependency.

Public product names and default installation/state paths use Relayhelm. Python
module/class names, existing SDK/entry-point group names, configuration keys,
explicit HERMES_* overrides, protocol fields, historical file names and genuine
Hermes model IDs remain where changing them would break existing integrations.
An existing Hermes installation is not automatically migrated or overwritten.

The inherited website documentation describes many upstream features. Live
upstream documentation links are reference material, not a Relayhelm-hosted
service. No upstream cloud account, code-signing credential, release artifact or
private plugin service is provided by renaming this repository.

Inherited website/container publishing and index automation are gated by the
repository variable `RELAYHELM_PUBLISH_ENABLED=true`. Configure your own release
services and credentials before enabling them. Ordinary source CI remains active.
