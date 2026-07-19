> python --version
> Python 3.12.9

> python -c "import platform; print(platform.platform())"
> Windows-11-10.0.26200-SP0

> Get-FileHash .\simcontract-0.3.0-source.zip -Algorithm SHA256
> 20174F5851E8C33D9BE29726673AB5F33053BD03B791D62FC06EB255AE5F2BFF

> python -m pip install --upgrade pip
> Requirement already satisfied: pip in [REDACTED_WORKDIR]\simcontract-0.3.0\.venv\lib\python3.12\site-packages (24.3.1)
Collecting pip
  Using cached pip-26.1.2-py3-none-any.whl.metadata (4.6 kB)
Using cached pip-26.1.2-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 24.3.1
    Uninstalling pip-24.3.1:
      Successfully uninstalled pip-24.3.1
Successfully installed pip-26.1.2

> python -m pip install ".[dev]"
> Processing .\.
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting PyYAML>=6.0 (from simcontract==0.3.0)
  Downloading pyyaml-6.0.3.tar.gz (130 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting pytest>=8.0 (from simcontract==0.3.0)
  Downloading pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
Collecting colorama>=0.4 (from pytest>=8.0->simcontract==0.3.0)
  Using cached colorama-0.4.6-py2.py3-none-any.whl.metadata (17 kB)
Collecting iniconfig>=1.0.1 (from pytest>=8.0->simcontract==0.3.0)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
Collecting packaging>=22 (from pytest>=8.0->simcontract==0.3.0)
  Using cached packaging-26.2-py3-none-any.whl.metadata (3.5 kB)
Collecting pluggy<2,>=1.5 (from pytest>=8.0->simcontract==0.3.0)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest>=8.0->simcontract==0.3.0)
  Using cached pygments-2.20.0-py3-none-any.whl.metadata (2.5 kB)
Downloading pytest-9.1.1-py3-none-any.whl (386 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached colorama-0.4.6-py2.py3-none-any.whl (25 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached packaging-26.2-py3-none-any.whl (100 kB)
Using cached pygments-2.20.0-py3-none-any.whl (1.2 MB)
Building wheels for collected packages: simcontract, PyYAML
  Building wheel for simcontract (pyproject.toml) ... done
  Created wheel for simcontract: filename=simcontract-0.3.0-py3-none-any.whl size=71460 sha256=79fbc1f1d11e092a8737674c3b2ed17514201f2c3b4bd2973052716ae0ba6c13
  Stored in directory: c:\users\[REDACTED_USER]\appdata\local\pip\cache\wheels\fa\da\a3\67f00786870bb27d20307438489da444c998377abb4fdcee80
  Building wheel for PyYAML (pyproject.toml) ... done
  Created wheel for PyYAML: filename=pyyaml-6.0.3-cp312-cp312-mingw_x86_64_ucrt_gnu.whl size=45487 sha256=b35a0a606c1a11fbf98732992b0a0adfe2b83a68fc9c14e56a1728154aea7c59
  Stored in directory: c:\users\[REDACTED_USER]\appdata\local\pip\cache\wheels\2a\40\b6\3634409f39c7dcb1652d049e48a7a4a63c09b2bdf6e8bb3d1d
Successfully built simcontract PyYAML
Installing collected packages: PyYAML, pygments, pluggy, packaging, iniconfig, colorama, simcontract, pytest
Successfully installed PyYAML-6.0.3 colorama-0.4.6 iniconfig-2.3.0 packaging-26.2 pluggy-1.6.0 pygments-2.20.0 pytest-9.1.1 simcontract-0.3.0

> python -m pytest -q
> ...................................................F........                                                                                                            [100%]
================================================================================== FAILURES ==================================================================================
_________________________________________________________________________ test_verify_intact_bundle __________________________________________________________________________

tmp_path = WindowsPath('C:/Users/[REDACTED_USER]/AppData/Local/Temp/pytest-of-[REDACTED_USER]/pytest-0/test_verify_intact_bundle0')

    def test_verify_intact_bundle(tmp_path):
        d = _bundle(tmp_path)
        verdict = verify_bundle(d)
        assert verdict["content_hash_ok"], verdict
>       assert verdict["files_ok"], verdict
E       AssertionError: {'bundle': 'C:\\Users\\[REDACTED_USER]\\AppData\\Local\\Temp\\pytest-of-[REDACTED_USER]\\pytest-0\\test_verify_intact_bundle0\\v', 'conten...ent_hash_recomputed': 'b5c9ef91e6939cfd2fb007225fdef4a6f449fadb309f42e3f921c1cc1473232e', 'content_hash_ok': True, ...}
E       assert False

tests\replay\test_bundle_verification.py:25: AssertionError
========================================================================== short test summary info ===========================================================================
FAILED tests/replay/test_bundle_verification.py::test_verify_intact_bundle - AssertionError: {'bundle': 'C:\\Users\\[REDACTED_USER]\\AppData\\Local\\Temp\\pytest-of-[REDACTED_USER]\\pytest-0\\test_verify_intact_bundle0\\v', 'conten...ent_hash_recomputed': 'b5c9ef91e6...
1 failed, 59 passed in 4.53s

> python -m simcontract.cli domains
> energy_market_v1       v0.2.0  roles=['regulatorx1', 'generatorx3', 'retailerx2']  scenarios=['baseline_v1', 'tight_supply_v1']
epidemic_policy_v1     v0.2.0  roles=['health_authorityx1', 'region_managerx3']  scenarios=['seed_outbreak_v1', 'second_wave_v1']
reference_stub         v0.2.0  roles=['agentx1']  scenarios=['default']

> python -m simcontract.cli run --domain energy_market_v1 --scenario baseline_v1 --seed 73 --rounds 5 --controllers all=rule --out benchmark-reproduction
> bundle written: benchmark-reproduction
content_hash:   dd73a35091a5fb609cea12fb8b84fa4858d7cbf87d0c4469765d672a3b0be7bc

> python -m simcontract.cli verify --bundle benchmark-reproduction
> {
  "bundle": "benchmark-reproduction",
  "content_hash_recorded": "dd73a35091a5fb609cea12fb8b84fa4858d7cbf87d0c4469765d672a3b0be7bc",
  "content_hash_recomputed": "dd73a35091a5fb609cea12fb8b84fa4858d7cbf87d0c4469765d672a3b0be7bc",
  "content_hash_ok": true,
  "files_ok": false,
  "files": {
    "config.snapshot.json": false,
    "decisions.jsonl": false,
    "domain_manifest.json": false,
    "fallback_events.jsonl": true,
    "llm_invocations.jsonl": true,
    "metrics.csv": false,
    "register.json": false,
    "rounds.json": false
  }
}

> python -m simcontract.cli replay --bundle benchmark-reproduction
> rounds compared: 5, equal: 5
REPLAY EQUIVALENT

> python -m pip freeze
> colorama==0.4.6
iniconfig==2.3.0
packaging==26.2
pluggy==1.6.0
Pygments==2.20.0
pytest==9.1.1
PyYAML==6.0.3
simcontract @ file:///[REDACTED_WORKDIR]/simcontract-0.3.0