# SimContract v0.3.1 — Independent Reproduction Protocol

**Protocol version:** 1.1
**Protocol date:** 2026-07-20 (fixed and published before any v0.3.1 reproduction is run)
**Target software:** SimContract v0.3.1 (Git tag `v0.3.1`, commit `8e96163`),
archived at Zenodo under the version-specific DOI below. Obtain the release
yourself and verify its integrity in Step 2.
**Note:** internet access is required for the installation step (pip downloads the build backend and the test dependency).

## Evaluated release

- **Version:** SimContract v0.3.1
- **Version-specific DOI:** [10.5281/zenodo.21447303](https://doi.org/10.5281/zenodo.21447303)
- **Published source archive SHA-256** (`simcontract-0.3.1-source.zip`): `83d8fca97bf21d7fffeb85428922e8ca30d8b69d48ef20083ea31ad8c23f54a8`

## Purpose

This protocol checks whether a non-contributor can independently reproduce the documented SimContract v0.3.1 deterministic workflow in a clean Python environment.

This is an independent reproduction check, not a usability study, user study, community-adoption claim, or validation of the demonstration domains as real-world forecasts.

## Obtaining the software (download it yourself)

For your own security, please do **not** run a zip file handed to you by the author. Obtain the frozen v0.3.1 release yourself from one of the two public, integrity-checked sources below. The author supplies only documents (this protocol and the report template), never executable material.

**Option A — Zenodo (archived source zip).** Open the archived record for
v0.3.1 and download `simcontract-0.3.1-source.zip`:

```text
https://doi.org/10.5281/zenodo.21447303
```

**Option B — GitHub (clone the tagged commit).** Clone the public repository and check out the `v0.3.1` tag:

```text
https://github.com/I-ueRya-n/SimContract-System-Architecture-Research
```

Use whichever you trust; both resolve to the same frozen v0.3.1 source. Verify integrity in Step 2.

Documents supplied by the author (no code):

- this protocol
- `SimContract_v0.3.1_Reproduction_Report_Template.md`

## Reproducer requirements

The reproducer should:

- not have contributed to SimContract's design, code, documentation, tests, or previous evidence generation;
- have basic familiarity with Python, `pip`, virtual environments, and terminal commands;
- make the first attempt without live step-by-step coaching;
- record any assistance, errors, or protocol deviations.

No GPU, API key, Docker, external dataset, or machine-learning expertise is required.

## How your report will be used (please read before you start)

Your completed report and logs are **intended to be published** as part of the reproduction evidence for SimContract v0.3.1. They may appear in a public GitHub issue, in an archived evidence package (Zenodo), and/or as supplementary material accompanying a research paper.

Before you begin, please note:

- **You may use a pseudonym.** In the report, the identifier can be your initials, a GitHub handle, or any identifier you choose. Your legal name is not required, and withholding it does not weaken the evidence — what matters is that you are not a contributor.
- **Optional fields.** Country/time zone and computer/hardware are optional and may be left blank. Operating system and Python version are the only environment details actually needed, because they evidence portability.
- **Relationship disclosure is required and will be public.** Whether you know the author personally, and whether you contributed to SimContract, must be answered honestly. Disclosing a personal connection is expected and does not invalidate the check; concealing one would.
- **Redact your own identifiers.** Before returning logs, remove your operating-system username and local file paths (for example, replace them with `[user]` / `[workdir]`); they are not needed and evidence nothing.
- **Private transit is fine.** If you send the ZIP to the author before publication, you may password-protect or encrypt it, or use any private channel you prefer. The final evidence is nevertheless intended to be public.
- **You may withdraw or request redaction** at any time before the evidence is archived or published.

By returning a completed report you consent to its publication as described above.

## What must be returned

Return one ZIP containing only:

```text
SimContract-v0.3.1-reproduction-[id]-[YYYY-MM-DD]/
├── reproduction-report.md
├── terminal-session.txt
└── benchmark-reproduction/
```

Optional, only when useful:

```text
screenshots/
```

`reproduction-report.md` must use the supplied report template.

`terminal-session.txt` should contain the commands and complete outputs from the installation, test, domains, run, verify, replay, environment, and package-version steps. Separate log files are not required. Redact your username and local paths before returning it.

---

# Procedure

## 1. Record the environment

Open PowerShell or a terminal.

Run:

```bash
python --version
python -c "import platform; print(platform.platform())"
```

If your system uses `python3`, substitute `python3` for `python`.

Copy both commands and outputs into `terminal-session.txt`.

## 2. Verify integrity of what you downloaded

**If you used Option A (Zenodo zip),** compute the archive SHA-256 and confirm
it equals the published value:

```text
83d8fca97bf21d7fffeb85428922e8ca30d8b69d48ef20083ea31ad8c23f54a8
```

- Windows PowerShell: `Get-FileHash .\simcontract-0.3.1-source.zip -Algorithm SHA256`
- macOS: `shasum -a 256 simcontract-0.3.1-source.zip`
- Linux: `sha256sum simcontract-0.3.1-source.zip`

**If you used Option B (GitHub clone),** check out the tag and confirm the
commit matches the one shown for the `v0.3.1` release:

```bash
git checkout v0.3.1
git rev-parse HEAD
```

Record the result in `terminal-session.txt`. Report any mismatch before continuing.

## 3. Enter the frozen source directory

**Option A (Zenodo zip):** extract `simcontract-0.3.1-source.zip` and enter the extracted `simcontract-0.3.1` directory.

**Option B (GitHub clone):** you are already at the repository root (it contains `pyproject.toml`); stay there.

Do not edit source files, YAML files, tests, benchmark files, expected hashes, or generated outputs.

## 4. Create a clean virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Confirm:

```bash
python --version
```

## 5. Install SimContract non-editably

Run:

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev]"
```

Do not use:

```bash
pip install -e .
```

Record all commands, outputs, warnings, and errors in `terminal-session.txt`.

## 6. Run the automated tests

From inside the extracted source directory:

```bash
python -m pytest -q
```

Expected result:

```text
66 passed
```

Record the exact result and elapsed time.

## 7. Run the installed package outside the source directory

Keep the virtual environment active.

Leave the source directory:

```bash
cd ..
```

Create a separate output directory:

```bash
mkdir simcontract-reproduction-output
cd simcontract-reproduction-output
```

## 8. List installed domains

Run:

```bash
python -m simcontract.cli domains
```

Expected domain identifiers:

```text
energy_market_v1
epidemic_policy_v1
reference_stub
```

## 9. Generate the deterministic benchmark

Run on one line:

```bash
python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 --seed 73 --rounds 5 --controllers all=rule --out benchmark-reproduction
```

Expected canonical content hash:

```text
dd73a35091a5fb609cea12fb8b84fa4858d7cbf87d0c4469765d672a3b0be7bc
```

Do not edit the generated `benchmark-reproduction/` directory.

## 10. Verify the evidence bundle

Run:

```bash
python -m simcontract.cli verify --bundle benchmark-reproduction
```

Expected conditions include:

```text
"content_hash_ok": true
"files_ok": true
```

Preserve the complete output. (On Windows, `files_ok: true` is the specific
behaviour v0.3.1 corrects relative to v0.3.0.)

## 11. Replay the recorded decisions

Run:

```bash
python -m simcontract.cli replay --bundle benchmark-reproduction
```

Expected result includes:

```text
rounds compared: 5, equal: 5
REPLAY EQUIVALENT
```

## 12. Record installed package versions

Run:

```bash
python -m pip freeze
```

Copy the complete output into `terminal-session.txt`.

## 13. Complete the report

Rename the supplied report template to:

```text
reproduction-report.md
```

Fill in every relevant field. Record:

- success or failure at each stage;
- first-attempt errors;
- any assistance received;
- files modified, if any;
- protocol deviations;
- actual and expected hashes;
- verification and replay results;
- approximate active completion time.

## 14. Return the evidence ZIP

Create:

```text
SimContract-v0.3.1-reproduction-[id]-[YYYY-MM-DD].zip
```

It should contain:

```text
reproduction-report.md
terminal-session.txt
benchmark-reproduction/
```

Screenshots are optional and should be included only when they clarify an error or output that was difficult to preserve as text.

## Interpretation boundary

One successful report supports only the following type of statement:

> An independent non-contributor reproduced the documented SimContract v0.3.1 deterministic workflow in a clean environment.

It does not establish usability, community adoption, universal cross-platform portability, clinical validity, or real-world forecasting validity.
