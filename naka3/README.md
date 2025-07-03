# naka3.sh

### Prerequsites

You need the following in your `$PATH`:

* `stacks-node`
* `blockstack-cli`
* `bitcoind` (version 25 or up)
* `bitcoin-cli`
* `stacks-signer`
* `jq`
* `dc`
* `bash` 5.0 or higher
* The usual GNU coreutils (`grep`, `sed`, etc)

### Quick Start

To run a playbook do this:

```bash
$ cd ./playbooks/one-miner
$ ./one-miner.sh start
```

To shut it down, run:

```bash
$ ./one-miner.sh stop
```

To resume it, run:

```bash
$ ./one-miner.sh resume
```

To create a snapshot, run:
> boot the chain to epoch 3.1 and then stop and create a snapshot

```bash
$ ./one-miner.sh snapshot create
```

To restore a snapshot, run:
```bash
$ ./one-miner.sh snapshot restore
```