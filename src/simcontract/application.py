"""Application facade (consolidated spec 6.8): the stable use-case surface.

CLI, experiment scripts, and any future API call these use cases; none of
them may reach engine internals or domain formulas directly. Concrete
domains stay behind the injected registry/assets — this module never imports
a domain.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from simcontract.analysis import AnalyzerRegistry, write_report
from simcontract.contracts import BundleView, DomainRegistry, RoleController
from simcontract.controllers import (
    BoundedLlmController,
    FreeLlmController,
    RandomValidController,
    RuleController,
    ScriptedHumanController,
    TopScoreController,
)
from simcontract.engine import ReplayReport, SessionRunner, replay_bundle
from simcontract.evidence import BundleEvidenceWriter, verify_bundle

AssetsFor = Callable[[str], tuple]   # alias -> (schema, observation, catalog, weights_for)


class Application:
    def __init__(self, registry: DomainRegistry, assets_for: AssetsFor,
                 analyzers: AnalyzerRegistry, llm_factory: Callable[..., Any]):
        self._registry = registry
        self._assets_for = assets_for
        self._analyzers = analyzers
        self._llm_factory = llm_factory

    # ------------------------------------------------------------------
    def list_domains(self) -> list[dict]:
        out = []
        for manifest in self._registry.manifests():
            out.append({
                "domain_id": manifest.domain_id,
                "domain_version": manifest.domain_version,
                "contract_version": manifest.contract_version,
                "roles": [f"{r.role}x{r.count}" for r in manifest.roles],
                "stages": list(manifest.stage_order),
                "scenarios": list(manifest.scenario_ids),
                "origin": manifest.origin,
            })
        return out

    # ------------------------------------------------------------------
    def build_controllers(self, adapter, schema, weights_for,
                          conditions: dict[str, str],
                          personas: dict[str, str | None],
                          llm=None,
                          human_scripts: dict[str, dict[int, dict]] | None = None,
                          ) -> dict[str, RoleController]:
        controllers: dict[str, RoleController] = {}
        scripts = human_scripts or {}
        for role in adapter.roles:
            for slot in role.slots():
                condition = conditions.get(slot, conditions.get("all"))
                if condition is None or condition == "unassigned":
                    continue
                persona = personas.get(slot)
                weights = weights_for(role.role, persona)
                if condition == "rule":
                    controllers[slot] = RuleController(
                        adapter.default_action_provider, persona)
                elif condition == "random_valid":
                    controllers[slot] = RandomValidController()
                elif condition == "top_score":
                    controllers[slot] = TopScoreController(weights)
                elif condition == "human_script":
                    controllers[slot] = ScriptedHumanController(
                        scripts.get(slot, {}), role.role)
                elif condition == "bounded_llm":
                    controllers[slot] = BoundedLlmController(llm, weights, persona)
                elif condition == "free_llm":
                    controllers[slot] = FreeLlmController(
                        llm, schema.fields_for(role.role), persona, role.role)
                else:
                    raise ValueError(f"unknown condition {condition!r} for {slot}")
        return controllers

    # ------------------------------------------------------------------
    def run_session(self, *, domain: str, scenario: str, seed: int, rounds: int,
                    conditions: dict[str, str], personas: dict[str, str | None],
                    out_dir: str | Path,
                    llm_base_url: str | None = None, llm_model: str | None = None,
                    human_scripts: dict[str, dict[int, dict]] | None = None,
                    extra_controllers: dict[str, RoleController] | None = None,
                    on_round=None) -> dict:
        adapter = self._registry.create(domain)
        schema, observation, catalog, weights_for = self._assets_for(domain)
        llm = self._llm_factory(llm_base_url, llm_model)
        controllers = self.build_controllers(adapter, schema, weights_for,
                                             conditions, personas, llm,
                                             human_scripts)
        if extra_controllers:
            controllers.update(extra_controllers)

        writer = BundleEvidenceWriter(out_dir)
        runner = SessionRunner(adapter, schema, observation, catalog, sink=writer)
        result = runner.run(scenario_id=scenario, run_seed=seed, rounds=rounds,
                            controllers=controllers, personas=personas,
                            on_round=on_round)
        return {
            "bundle": str(writer.path),
            "content_hash": writer.content_hash,
            "rounds": len(result.rounds),
            "events": len(result.events),
            "result": result,
        }

    # ------------------------------------------------------------------
    def replay_run(self, bundle_dir: str | Path) -> ReplayReport:
        bundle = BundleView.load(bundle_dir)
        alias = bundle.manifest.domain_id
        adapter = self._registry.create(alias)
        schema, observation, catalog, _ = self._assets_for(alias)
        return replay_bundle(bundle, adapter, schema, observation, catalog)

    def verify_bundle(self, bundle_dir: str | Path) -> dict:
        return verify_bundle(bundle_dir)

    # ------------------------------------------------------------------
    def analyse_bundles(self, bundle_dirs: list[str | Path],
                        analyzer_ids: list[str] | None = None,
                        out: str | Path = "results/analysis") -> Path:
        bundles = [BundleView.load(p) for p in bundle_dirs]
        ids = analyzer_ids or self._analyzers.ids()
        results = [self._analyzers.get(a).run(bundles) for a in ids]
        return write_report(results, out)
