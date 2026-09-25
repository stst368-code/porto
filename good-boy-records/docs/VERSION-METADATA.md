# Version metadata rules

`version:` is now opaque. Suffixes such as `-a`, `-b`, and `-c` are part of the version name and are never interpreted as cassette sides.

Examples:

```yaml
version: one-off-c
```

is simply version `one-off-c`.

If cassette-side metadata is actually wanted, specify it explicitly:

```yaml
version: alternate-take
side: B
```

Explicit A, B, and C sides are accepted.
