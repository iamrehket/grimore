"""Build git histories with known component lifecycle shapes.

The digest walks first-parent history and reads each component's `status`
across the diff, so its tests need histories with specific shapes: squash
landings beside merge landings, several transitions collapsed into one landed
commit, timestamps that do not increase, and clones truncated part-way.
Assembling those inline buries the shape under a dozen git calls, and the
shapes are easy to get subtly wrong - a "squash" that is really a merge tests
nothing.

Dates are supplied as ISO strings carrying an explicit offset, for example
"2026-01-01T01:30:00+1300". The offset is load-bearing: the digest resolves
its boundary in UTC, so a commit's local day and its UTC day can differ, and
that difference is a thing tests need to construct on purpose.
"""

import subprocess
from pathlib import Path

from helpers import write_component


class History:
    """A throwaway repository whose history is built one landing at a time."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._git("init", "-b", "main")
        # Per-repository and never inherited by a clone; without it git falls
        # back to hostname auto-detection, which fails on a bare runner.
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")

    def _git(self, *args, when=None, committed=None, cwd=None):
        env = None
        if when is not None or committed is not None:
            import os

            env = dict(os.environ)
            if when is not None:
                env["GIT_AUTHOR_DATE"] = when
                env["GIT_COMMITTER_DATE"] = when
            if committed is not None:
                env["GIT_COMMITTER_DATE"] = committed
        r = subprocess.run(
            ["git", *args],
            cwd=cwd or self.root,
            capture_output=True,
            text=True,
            env=env,
        )
        assert r.returncode == 0, f"git {' '.join(args)}\n{r.stderr}"
        return r.stdout

    # -- store mutation -------------------------------------------------

    def write(self, ctype, slug, *, status="draft", date="2026-07-24", **kw):
        """Create or overwrite a component. Overwriting is how a status flips."""
        return write_component(self.root, ctype, slug, status=status, date=date, **kw)

    def delete(self, ctype, slug):
        """Remove a component file - the transition the schema forbids."""
        (self.root / "docs" / "components" / ctype / f"{slug}.md").unlink()

    # -- landings -------------------------------------------------------

    def commit(self, msg, *, when=None, committed=None):
        self._git("add", "-A")
        self._git("commit", "-m", msg, when=when, committed=committed)
        return self.head()

    def start_branch(self, name):
        self._git("checkout", "-q", "-b", name)

    def land_squash(self, branch, msg, *, when=None, committed=None):
        """Collapse a branch into one commit on main, as pull requests #14-#17 did.

        The result has exactly one parent, so first-parent and a full walk see
        the same thing - and every transition inside the branch collapses into
        this single commit.
        """
        self._git("checkout", "-q", "main")
        self._git("merge", "--squash", branch)
        self._git("commit", "-m", msg, when=when, committed=committed)
        return self.head()

    def land_merge(self, branch, msg, *, when=None, committed=None):
        """Merge a branch into main with a real merge commit, as #8 and #10-#13 did.

        The result has two parents, so a full walk sees the branch's own
        commits while a first-parent walk sees only this one.
        """
        self._git("checkout", "-q", "main")
        self._git("merge", "--no-ff", "--no-commit", branch)
        self._git("commit", "-m", msg, when=when, committed=committed)
        return self.head()

    # -- inspection -----------------------------------------------------

    def head(self):
        return self._git("rev-parse", "HEAD").strip()

    def parents(self, rev="HEAD"):
        return self._git("rev-list", "--parents", "-n1", rev).split()[1:]

    def first_parent_shas(self):
        """Oldest first, matching the order the digest walks."""
        return self._git("rev-list", "--first-parent", "--reverse", "HEAD").split()

    def committer_epoch(self, rev="HEAD"):
        return int(self._git("log", "-1", "--format=%ct", rev).strip())

    def shallow_clone(self, dest, depth):
        """Clone truncated to `depth` commits.

        A local path clone ignores --depth and hardlinks the object store - git
        warns, but the warning is easy to miss and the clone is not shallow.
        A file:// URL is what actually truncates, so this asserts the result
        rather than trusting it.
        """
        dest = Path(dest)
        self._git(
            "clone",
            "--depth",
            str(depth),
            f"file://{self.root.resolve()}",
            str(dest),
            cwd=dest.parent,
        )
        self._git("config", "user.email", "test@example.com", cwd=dest)
        self._git("config", "user.name", "Test", cwd=dest)
        shallow = self._git("rev-parse", "--is-shallow-repository", cwd=dest).strip()
        assert shallow == "true", f"clone of {self.root} is not shallow"
        return dest
