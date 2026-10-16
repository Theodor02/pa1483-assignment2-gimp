# PA1483 Assignment 2: GIMP

Scripts and measurement data for Assignment 2 in PA1483 Software Architecture at Blekinge Tekniska Högskola (group 10). The assignment analyses the architecture of [GIMP](https://gitlab.gnome.org/GNOME/gimp) and measures its quality attributes: modifiability, testability and usability.

Everything here is used to produce the measurements in the report, so the numbers can be reproduced.

## Structure

```
testability/
  gimp_testability.py               measurement script
  appendix-testability-script.tex   the script as a LaTeX appendix
```

Folders for the other quality attributes are added as their scripts are written.

## Setup

Requires Python 3 and Git. No extra packages.

Clone GIMP into the repository root (it is ignored by Git):

```
git clone --depth 1 https://gitlab.gnome.org/GNOME/gimp.git
```

## Testability

```
python testability/gimp_testability.py gimp
```

Leave out `gimp` to fetch only the GitLab API numbers. Set `SINCE` at the top of the script to change the measurement window.

| Metric | Definition | Source |
|---|---|---|
| Platform Test Coverage | Built OS/architecture configurations that also run the test suite | `.gitlab-ci.yml` |
| Pipeline Success Rate | Successful / (successful + failed) pipelines on `master`, cancelled excluded | GitLab API |
| Module Test Coverage | Tests registered per module | `meson.build` files |

### Results (16 July to 15 October 2026)

Source commit `d8d30252`, test report from pipeline #1126996.

**Platform Test Coverage:** 1 of 11 configurations (9.1%). Only Debian x86_64 runs `ninja test`.

**Pipeline Success Rate**

| Trigger | Success | Failed | Cancelled | PSR |
|---|---|---|---|---|
| Commit | 499 | 47 | 109 | 91.4% |
| Scheduled | 47 | 29 | 2 | 61.8% |
| Manual | 13 | 10 | 4 | 56.5% |
| Total | 559 | 86 | 115 | 86.7% |

**Module Test Coverage**

| Module | Running tests |
|---|---|
| Core | 3 |
| Display | 0 (4 test files disabled) |
| Tools | 0 (1 test file disabled) |
| Config | 1 |
| Plug-in interface | 15 |
| Desktop files | 2 |

All 21 unit tests passed in 2.6 s. The file import tests ran 1597 cases across 32 formats: 1595 passed, 2 skipped.
