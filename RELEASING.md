# Releasing ATLAS

Releases are published to PyPI as `atlas-eng` by
[`.github/workflows/release.yml`](.github/workflows/release.yml) when a
version tag is pushed. No API token is stored anywhere: PyPI trusts this
repository's workflow directly ([Trusted Publishing](https://docs.pypi.org/trusted-publishers/)).

## One-time setup (maintainer, on the PyPI websites)

Do this once, before the first release. It needs a PyPI account and a
TestPyPI account (they are separate sites with separate logins).

1. On **https://test.pypi.org/manage/account/publishing/**, add a *pending
   publisher* with:

   | Field | Value |
   |---|---|
   | PyPI Project Name | `atlas-eng` |
   | Owner | `sahil-mangla` |
   | Repository name | `atlas` |
   | Workflow name | `release.yml` |
   | Environment name | `testpypi` |

2. On **https://pypi.org/manage/account/publishing/**, add the same, except
   **Environment name** is `pypi`.

The pending publisher reserves nothing by itself: the first successful
upload creates the project. Until then anyone could register the name, so do
the first release soon after.

3. Optional but recommended: in the repository's **Settings → Environments
   → pypi**, add yourself as a *required reviewer*, so every PyPI upload
   waits for your approval after the TestPyPI checks pass.

## Dry run

**Actions → Release → Run workflow** builds the package, uploads it to
TestPyPI, and installs and runs what TestPyPI serves on Linux, macOS and
Windows. It never publishes to PyPI. TestPyPI accepts each version only
once, so a later real release of the same version skips that upload and
re-tests the copy already there.

## Each release

1. Make sure CI is green on `main`.
2. Set the version in `pyproject.toml` (`[project] version`).
3. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`
   and start a new empty `## [Unreleased]` above it. The release notes are
   taken from this section.
4. Commit, then tag and push:

   ```bash
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

The workflow then:

1. checks the tag matches the version and the changelog has its section;
2. builds the wheel and sdist once, and validates them with `twine check`;
3. publishes to TestPyPI and installs that file on every OS;
4. publishes the **same files** to PyPI (after your approval, if set up);
5. installs `atlas-eng[all]` from PyPI on every OS with Python 3.12 and 3.13,
   runs the offline smoke test, and checks `uvx atlas-eng`;
6. creates the GitHub release with the changelog section and the files.

Tags such as `v1.2.0rc1` publish a pre-release: pip ignores it unless asked
(`pip install --pre atlas-eng`), and the GitHub release is marked as such.

## If something fails

- **Before PyPI** (steps 1–3): nothing public changed except possibly
  TestPyPI. Fix the problem, delete and re-push the tag
  (`git push --delete origin vX.Y.Z`, then tag again).
- **After PyPI** (steps 5–6): a published version can never be replaced.
  Yank it on PyPI if it is broken, fix the problem, and release a new patch
  version.
