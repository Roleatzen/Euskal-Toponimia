
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


@dataclass
class Element:
    id: str
    form: str
    meaning: str
    category: str
    kind: str
    positions: list[str]
    variants: list[str]
    productivity: float
    antiquity: str
    combination_tags: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)


@dataclass
class Pattern:
    id: str
    name: str
    slots: list[str]
    meaning_template: str
    weight: float
    modes: list[str]


@dataclass
class Rule:
    id: str
    name: str
    kind: str
    priority: int
    modes: list[str]
    condition: str
    replacement: str
    note: str = ""


class ToponymGenerator:
    """Rule-based Basque/proto-Basque toponymy generator.

    The generator deliberately separates:
      1. lexical selection,
      2. morphological compatibility,
      3. composition,
      4. attested/operational phonological rules,
      5. historical/proto transformations.

    It does NOT claim that every generated form is historically attested.
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.elements = self._load_json("elements.json")
        self.patterns = self._load_json("patterns.json")
        self.rules = self._load_json("rules.json")

    def _load_json(self, filename: str) -> Any:
        with open(DATA_DIR / filename, encoding="utf-8") as f:
            return json.load(f)

    def _elements(self) -> dict[str, Element]:
        return {
            e["id"]: Element(**e)
            for e in self.elements
        }

    def _patterns(self, mode: str) -> list[Pattern]:
        return [
            Pattern(**p) for p in self.patterns
            if mode in p["modes"]
        ]

    def _choose(self, items, weights):
        return self.rng.choices(items, weights=weights, k=1)[0]

    def _choose_element(self, slot: str, mode: str) -> Element:
        elements = self._elements()

        if slot in elements:
            return elements[slot]

        candidates = []
        for e in elements.values():
            if slot in e.combination_tags or slot == e.category:
                if mode == "documental" and e.antiquity == "MODERNA":
                    continue
                # Very low-productivity lexicalized entries are not useful
                # as freely productive roots.
                if e.productivity <= 0.25 and e.kind == "LEXEMA":
                    continue
                candidates.append(e)

        if not candidates:
            raise ValueError(f"No hay elementos compatibles con el slot {slot!r}")

        return self._choose(
            candidates,
            [max(0.01, e.productivity) for e in candidates]
        )

    def _compatible(self, left: Element, right: Element) -> tuple[bool, str]:
        if right.kind == "SUFIJO" and "FINAL" not in right.positions:
            return False, "El sufijo no está marcado como final."

        if left.kind == "SUFIJO" and right.kind == "SUFIJO":
            return False, "No se encadenan dos sufijos toponímicos."

        if left.id in {"AGA", "ETA", "DI", "TI", "TEGI"}:
            return False, f"{left.form} es terminal en esta versión."

        if right.id in {"DI", "TI"} and "VEGETACION" not in left.combination_tags:
            return False, "-di/-ti se restringen aquí a bases vegetales."

        if right.id == "TEGI":
            allowed = {"ASENTAMIENTO", "ACTIVIDAD", "PERSONA", "OFICIO", "LEXEMA"}
            if not any(tag in allowed for tag in left.combination_tags):
                return False, "La base no es adecuada para -tegi."

        if right.id in {"AGA", "ETA"}:
            allowed = {"VEGETACION", "RELIEVE", "AGUA", "FAUNA",
                       "ASENTAMIENTO", "LEXEMA_GEOGRAFICO"}
            if not any(tag in allowed for tag in left.combination_tags):
                return False, "La base no está marcada como nominal/geográfica para -aga/-eta."

        return True, ""

    def _join(self, left: Element, right: Element) -> tuple[str, list[str]]:
        """Compose two elements and return form + applied-rule IDs.

        Rules here are intentionally conservative. The rules for -aga/-eta
        block ordinary composition alternations affecting the final vowel
        of the base, matching the special behaviour discussed in the project
        documentation.
        """
        left_form = left.form if hasattr(left, "form") else left["form"]
        right_form = right.form if hasattr(right, "form") else right["form"]
        right_id = right.id if hasattr(right, "id") else right.id if hasattr(right, "id") else right["id"]
        applied = []

        # Special topographic suffixes: preserve the base's final vowel.
        if right_id in {"AGA", "ETA"}:
            return left_form + right_form.lstrip("-"), applied

        # Ordinary compound alternations.
        # These are only applied to the first member.
        if right_id not in {"KO"}:
            if left_form.endswith(("di", "gi")):
                left_form = left_form[:-2] + "t"
                applied.append("F01_DI_GI_TO_T")

            elif left_form.endswith(("e", "o", "u")):
                left_form = left_form[:-1] + "a"
                applied.append("F03_FINAL_VOWEL_TO_A")

            elif left_form.endswith("n"):
                left_form = left_form[:-1] + "r"
                applied.append("F04_FINAL_N_TO_R")

            elif left_form.endswith("ra"):
                left_form = left_form[:-2] + "l"
                applied.append("F05_RA_TO_L")

            elif left_form.endswith("re"):
                left_form = left_form[:-2] + "l"
                applied.append("F05_RE_TO_L")

            elif left_form.endswith("ri"):
                left_form = left_form[:-2] + "l"
                applied.append("F05_RI_TO_L")

        return left_form + right_form.lstrip("-"), applied

    def _historical_transform(self, form: str, mode: str) -> tuple[str, list[str]]:
        applied = []

        if mode not in {"historico", "proto"}:
            return form, applied

        # Conservative historical variants, never presented as mandatory.
        # They are stochastic to avoid making every generated form look alike.
        if self.rng.random() < 0.20:
            old = form
            form = re.sub(r"^h", "", form)
            if form != old:
                applied.append("H01_INITIAL_H_LOSS_OPTIONAL")

        if mode == "proto" and self.rng.random() < 0.15:
            old = form
            # Optional simplification often seen in historical/vernacular
            # material; intentionally marked experimental.
            form = form.replace("rr", "r")
            if form != old:
                applied.append("P01_RR_SIMPLIFICATION_EXPERIMENTAL")

        return form, applied

    def _render_meaning(self, pattern: Pattern, chosen: list[Element]) -> str:
        values = {
            "A": chosen[0].meaning if len(chosen) > 0 else "",
            "B": chosen[1].meaning if len(chosen) > 1 else "",
        }
        return pattern.meaning_template.format(**values)

    def generate(self, mode: str = "vasco") -> dict[str, Any]:
        if mode not in {"documental", "vasco", "historico", "proto"}:
            raise ValueError("Modo: documental, vasco, historico o proto")

        patterns = self._patterns(mode)
        if not patterns:
            raise ValueError(f"No hay patrones para el modo {mode!r}")

        pattern = self._choose(
            patterns,
            [max(0.01, p.weight) for p in patterns]
        )

        # Try several lexical selections until all adjacent combinations
        # satisfy the morphology rules.
        for _ in range(50):
            chosen = [self._choose_element(slot, mode) for slot in pattern.slots]

            valid = True
            for left, right in zip(chosen, chosen[1:]):
                ok, _reason = self._compatible(left, right)
                if not ok:
                    valid = False
                    break

            if valid:
                break
        else:
            raise RuntimeError(
                f"No se pudo resolver el patrón {pattern.id} con las "
                f"restricciones actuales."
            )

        form = chosen[0].form
        applied = []

        for nxt in chosen[1:]:
            left = form_as_element(form)
            form, rules = self._join(left, nxt)
            applied.extend(rules)

        form, historical_rules = self._historical_transform(form, mode)
        applied.extend(historical_rules)

        return {
            "toponym": form.capitalize(),
            "meaning": self._render_meaning(pattern, chosen),
            "mode": mode,
            "pattern": pattern.name,
            "components": [
                {
                    "id": e.id,
                    "form": e.form,
                    "meaning": e.meaning,
                    "category": e.category,
                }
                for e in chosen
            ],
            "rules": applied,
            "confidence": self._confidence(mode, applied),
            "disclaimer": self._disclaimer(mode),
        }


    def _confidence(self, mode: str, rules: list[str]) -> str:
        if mode == "documental":
            return "alta para la estructura; no implica atestiguación del topónimo generado"
        if mode == "vasco":
            return "plausibilidad generativa"
        if mode == "historico":
            return "plausibilidad histórica aproximada"
        return "reconstrucción experimental; no equivale a una forma protohistórica documentada"

    def _disclaimer(self, mode: str) -> str:
        if mode == "proto":
            return "Forma generada/reconstruida. No debe citarse como topónimo histórico real."
        return "Forma generada. La plausibilidad no implica atestiguación documental."


def form_as_element(form: str) -> dict[str, Any]:
    """Adapter used internally after the first composition step."""
    return {
        "id": "__COMPOSED__",
        "form": form,
        "meaning": "",
        "category": "COMPOSED",
        "kind": "LEXEMA",
        "positions": ["INICIAL"],
        "variants": [],
        "productivity": 1.0,
        "antiquity": "ANTIGUA",
        "combination_tags": ["LEXEMA", "LEXEMA_GEOGRAFICO"],
        "restrictions": [],
    }


def generate_many(n: int = 20, mode: str = "vasco", seed: int | None = None):
    gen = ToponymGenerator(seed=seed)
    return [gen.generate(mode) for _ in range(n)]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generador de toponimia vasca/protovasca"
    )
    parser.add_argument("-n", "--number", type=int, default=20)
    parser.add_argument(
        "-m", "--mode",
        choices=["documental", "vasco", "historico", "proto"],
        default="vasco"
    )
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    for result in generate_many(args.number, args.mode, args.seed):
        print(
            f"{result['toponym']:<18} — {result['meaning']}"
            f"  [{result['pattern']}]"
        )
